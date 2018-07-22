
import os
import psutil as ps
import glob
import sys
from copy import copy

import lattice
import utils.numpy_utils as numpy_utils
from utils.python_utils import *

from shape_converter import SubDomain

# import sailfish
sys.path.append('../sailfish')
from sailfish.controller import LBSimulationController
from sailfish.lb_single import LBFluidSim
from sailfish.lb_base import LBForcedSim

import numpy as np

class Domain(object):

  def __init__(self, config, save_dir):
    self.save_dir = save_dir
    self.lb_to_ln = config.lb_to_ln
    self.max_sim_iters = config.max_sim_iters
    self.debug_sailfish = config.debug_sailfish
    self.train_sim_dir = config.train_sim_dir
    self.train_autoencoder = config.train_autoencoder
 
    self.DxQy = lattice.TYPES[config.DxQy]()

    # get padding TODO code not clean here 
    if self.DxQy.D == 2:
      self.padding_type = ['zero', 'zero']
      if self.domain.periodic_x:
        self.padding_type[0] = 'periodic'
      if self.domain.periodic_y:
        self.padding_type[1] = 'periodic'
    if self.DxQy.D == 3:
      self.padding_type = ['zero', 'zero', 'zero']
      if self.domain.periodic_x:
        self.padding_type[0] = 'periodic'
      if self.domain.periodic_y:
        self.padding_type[1] = 'periodic'
      if self.domain.periodic_z:
        self.padding_type[2] = 'periodic'

class TrainDomain(Domain):
  def __init__(self, config, save_dir):
    super(Domain, self).__init__(config, save_dir)

    # data point for training (both uncompressed and compressed)
    self.data_points = []
    self.cdata_points = []

  def select_rand_dp(self):
    point_ind = np.random.randint(0, len(self.data_points))
    return self.data_points[point_ind]

  def select_rand_cdp(self, augment=False):
    point_ind = np.random.randint(0, len(self.cdata_points))
    return self.cdata_points[point_ind]

  def read_dp(self, dp, add_batch=False):
    # read state
    state = self.read_state(dp.ind, dp.state_subdomain, add_batch)

    # read boundary
    boundary = self.read_boundary(dp.state_subdomain, add_batch)

    # read seq states
    seq_state = []
    for i in xrange(dp.seq_length):
      seq_state.append(self.read_state(dp.ind + i, dp.seq_state_subdomain, add_batch))

    return state, boundary, seq_state

  def read_cdp(self, cdp, add_batch=False):
    # read state
    cstate = self.read_cstate(cdp.ind, cdp.state_subdomain, add_batch)

    # read boundary
    cboundary = self.read_cboundary(cdp.state_subdomain, add_batch)

    # read seq states
    seq_cstate = []
    for i in xrange(cdp.seq_length):
      seq_cstate.append(self.read_cstate(cdp.ind + i, cdp.seq_cstate_subdomain, add_batch))

    return cstate, cboundary, seq_cstate

  def add_dp(self, dp):
    self.data_points.append(dp)

  def add_dp(self, cdp):
    self.cdata_points.append(cdp)

  def save_dps(self):
    datapoint_filename = self.save_dir + '/data_points.txt'
    with open(datapoint_filename, "w") as f:
      for point in self.data_points:
        save_string = point.to_string()
        f.write(save_string)

  def save_cdps(self):
    datapoint_filename = self.save_dir + '/cdata_points.txt'
    with open(datapoint_filename, "w") as f:
      for point in self.cdata_points:
        save_string = point.to_string()
        f.write(save_string)

  def load_dp(self):
    datapoint_filename = self.save_dir + '/data_points.txt'
    with open(datapoint_filename, "r") as f:
      string_points = f.readlines()
      for p in string_points: 
        d = DataPoint(0,0,0,0)
        d.load_string(p)
        self.data_points.append(d)

  def load_cdp(self):
    datapoint_filename = self.save_dir + '/cdata_points.txt'
    with open(datapoint_filename, "r") as f:
      string_points = f.readlines()
      for p in string_points: 
        d = DataPoint(0,0,0,0)
        d.load_string(p)
        self.cdata_points.append(d)

class SailfishDomain(Domain, SailfishWrapper):
  def __init__(self, config, save_dir):
    super(Domain, self).__init__(config, save_dir)
    super(Sailfish, self).__init__(config)

  @classmethod
  def add_options(cls, group, dim):
    pass

  @classmethod
  def update_defaults(cls, defaults):
    pass

  def read_state(self, iteration, subdomain=None, add_batch=False, return_padding=True):
    # load flow file
    state_file = self.iter_to_state_filename(iteration)
    state = np.load(state_file)
    state = state.f.dist0a[:,1:-1,1:self.sim_shape[1]+1]
    state = state.astype(np.float32)
    state = np.swapaxes(state, 0, 1)
    state = np.swapaxes(state, 1, 2)
    state = self.DxQy.subtract_lattice(state)
    if subdomain is not None:
      state, pad_state = numpy_utils.mobius_extract(state, subdomain,
                                            padding_type=self.padding_type,
                                            return_padding=True)
    if add_batch:
      state = np.expand_dims(state, axis=0)
      if subdomain is not None:
        pad_state = np.expand_dims(pad_state, axis=0)
    if subdomain is not None:
      return (state, pad_state)
    else:
      return state

  def read_boundary(self, subdomain=None, add_batch=False, return_padding=True):
    boundary_file = self.boundary_filename()
    boundary = None
    if os.path.isfile(boundary_file):
      boundary = np.load(boundary_file)
      boundary = boundary.astype(np.float32)
      boundary = boundary[1:-1,1:-1]
      if subdomain is not None:
        boundary, pad_boundary = numpy_utils.mobius_extract(boundary, subdomain,
                                              padding_type=self.padding_type,
                                              return_padding=True)
    if add_batch:
      boundary     = np.expand_dims(boundary, axis=0)
      pad_boundary = np.expand_dims(pad_boundary, axis=0)
    if subdomain is not None:
      return (boundary, pad_boundary)
    else:
      return boundary

  def read_cstate(self, iteration, subdomain=None, add_batch=False, return_padding=True):
    # load flow file
    cstate_file = self.iter_to_cstate_filename(iteration)
    cstate = np.load(cstate_file)
    if subdomain is not None:
      cstate, pad_cstate = numpy_utils.mobius_extract(cstate, subdomain,
                                                padding_type=self.padding_type,
                                                return_padding=True)
    if add_batch:
      cstate = np.expand_dims(cstate, axis=0)
      if subdomain is not None:
        pad_cstate = np.expand_dims(pad_cstate, axis=0)
    if subdomain is not None:
      return (cstate, pad_cstate)
    else:
      return cstate

  def read_cboundary(self, iteration, subdomain=None, add_batch=False, return_padding=True):
    cboundary_file = self.cboundary_filename()
    cboundary = np.load(cboundary_file)
    if subdomain is not None:
      cboundary, pad_boundary = numpy_utils.mobius_extract(boundary, subdomain,
                                            padding_type=self.padding_type,
                                            return_padding=True)
    if add_batch:
      cboundary     = np.expand_dims(cboundary, axis=0)
      if subdomain is not None:
        pad_cboundary = np.expand_dims(pad_cboundary, axis=0)
    if subdomain is not None:
      return (cboundary, pad_cboundary)
    else:
      return cboundary

  def read_vel_rho(self, iteration, subdomain=None, add_batch=False):
    state = self.read_state(iteration, subdomain, add_batch=add_batch)
    vel = self.DxQy.lattice_to_vel(state)
    rho = self.DxQy.lattice_to_rho(state)
    return vel, rho

  def need_to_generate(self):
    # check if need to generate train data or not
    need = False
    cpoints = self.list_cpoints()
    if len(cpoints) != self.num_cpoints:
      need = True 
    boundary_file = self.boundary_file()
    if not os.path.isfile(boundary_file):
      need = True 
    return need 

  def generate_train_data(self):
    self.new_sim(self.num_cpoints)

class JHTDBDomain(Domain, JHTDBWrapper):
  def __init__(self, config, save_dir):
    super(Domain, self).__init__(config, save_dir)
    super(JHTDBWrapper, self).__init__(config, save_dir)

  def add_options(cls, group, dim):
    pass

  def read_state(self, iteration, subdomain=None, add_batch=False, return_padding=True):
    state_file = self.save_dir + self.make_filename(subdomain, iteration)
    state_stream = h5py.File(state_file)
    key_vel      = state_stream.keys()[5]
    key_pressure = state_stream.keys()[4]
    vel = np.array(state_stream[key_vel])
    pressure = np.array(state_stream[key_pressure])
    state_stream = None
    state = np.concatenate([vel/10.0, pressure/3.0], axis=-1)
    state = state.astype(np.float32)
    if add_batch:
      state = np.expand_dims(state, axis=0)
    if return_padding:
      state_pad = np.zeros(list(state.shape[:-1]) + [1])
      return state, state_pad
    else:
      return state

  def read_boundary(self, subdomain=None, add_batch=False, return_padding=True):
    return None

  def read_cstate(self, iteration, subdomain=None, add_batch=False, return_padding=True):
    # load flow file
    state_file = self.save_dir + self.make_filename(subdomain, iteration, filetype='npy')

    cstate = np.load(state_file)

    if add_batch:
      cstate = np.expand_dims(cstate, axis=0)
    if return_padding:
      cstate_pad = np.zeros(list(cstate.shape[:-1]) + [1])
      return cstate, cstate_pad
    else:
      return cstate

  def read_cboundary(self, subdomain=None, add_batch=False, return_padding=True):
    return None

  def read_vel_rho(self, iteration, subdomain=None, add_batch=False):
    state = self.read_state(iteration, subdomain, add_batch, return_padding=False)
    return state[...,0:3], state[...,3:4]

class TrainSailfishDomain(SailfishDomain, TrainDomain):
  def __init__(self, config, save_dir):
    super(SailfishDomain, self).__init__(config, save_dir)
    super(TrainDomain, self).__init__(config, save_dir)

    # check if need to generate data and do so
    if self.need_to_generate()
      self.generate_train_data()

  def need_to_generate(self):
    # check if need to generate train data or not
    need = False
    cpoints = self.list_cpoints()
    if len(cpoints) != self.num_cpoints:
      need = True 
    boundary_file = self.boundary_file()
    if not os.path.isfile(boundary_file):
      need = True 
    return need 

  def generate_train_data(self):
    self.new_sim(self.num_cpoints)

  def generate_rand_dp(self, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio):
    # select random index
    state_files = self.list_state_filenames()
    ind = np.random.randint(1, len(state_files) - seq_length)

    # select random pos to grab from data
    rand_pos = [np.random.randint(-input_cshape[0], self.sim_shape[0]/cratio+1),
                np.random.randint(-input_cshape[1], self.sim_shape[1]/cratio+1)]
    cstate_subdomain = SubDomain(rand_pos, input_cshape)

    # get state subdomain and geometry_subdomain
    state_subdomain = state_shape_converter.out_in_subdomain(copy(cstate_subdomain))

    # get seq state subdomain
    seq_state_subdomain = seq_state_shape_converter.in_out_subdomain(copy(state_subdomain))

    # data point and return it
    return DataPoint(ind, seq_length, state_subdomain, seq_state_subdomain)

  def generate_rand_cdp(self, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio, encode_state, encode_boundary):
    # select random index
    state_files = self.list_state_filenames()
    ind = np.random.randint(1, len(state_files) - seq_length)

    # select random pos to grab from data
    rand_pos = [np.random.randint(-input_cshape[0], self.sim_shape[0]/cratio+1),
                np.random.randint(-input_cshape[1], self.sim_shape[1]/cratio+1)]
    cstate_subdomain = SubDomain(rand_pos, input_cshape)

    # get state subdomain and geometry_subdomain
    state_subdomain = state_shape_converter.out_in_subdomain(copy(cstate_subdomain))

    # get seq state subdomain
    seq_state_subdomain = seq_state_shape_converter.in_out_subdomain(copy(state_subdomain))

    # generate cstate files if needed
    for i in xrange(seq_length):
      if not os.isfile(self.iter_to_cstate_filename(ind + i)):
        state = self.read_state(ind+i, subdomain=None, add_batch=True, return_padding=True)
        cstate = encode_state({'state':state})[0]
        np.save(self.iter_to_cstate_filename(ind + i), cstate)
      
    # generate cboundary file if needed
    if not os.isfile(self.cboundary_filename()):
      boundary = self.read_boundary(subdomain=None, add_batch=True, return_padding=True)
      cboundary = encode_boundary({'boundary':boundary})[0]
      np.save(self.cboundary_filename(), cboundary)

    # data point and return it
    return DataPoint(ind, seq_length, state_subdomain, seq_state_subdomain)

  def add_rand_dps(self, num_points, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio):
    for i in xrange(num_points):
      # make datapoint and add to list
      self.data_points.append(self.generate_rand_dp(seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio))

  def add_rand_cdps(self, num_points, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio):
    for i in xrange(num_points):
      # make datapoint and add to list
      self.data_points.append(self.generate_rand_cdp(seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio))


class TrainJHTDBDomain(JHTDBDomain, TrainDomain):
  def __init__(self, config, save_dir):
    super(JHTDBDomain, self).__init__(config, save_dir)
    super(TrainDomain, self).__init__(config, save_dir)
 
  def download_dp_worker(self):
    while True:
      (seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio) = self.queue.get()
      # make datapoint and add to list
      self.data_points.append(self.generate_rand_dp(seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio))
      self.queue.task_done()

  def add_rand_dps(self, num_points, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio):
    self.save_data_points()
    self.queue.join()
    for i in tqdm(xrange(num_points)):
      self.queue.put((seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio))

  def add_rand_cdps(self, num_points, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio, encode_state, encode_boundary):
    self.save_data_points()
    self.queue.join()
    for i in tqdm(xrange(num_points)):
      self.queue.put((seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio, encode_state, encode_boundary))

  def generate_rand_dp(self, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio):
    # select random index
    ind = np.random.randint(0, (5024/self.step_ratio)-seq_length)

    # select random pos to grab from data
    rand_pos = [np.random.randint(input_cshape[0]+16, self.sim_shape[0]/cratio - input_cshape[0] - 16),
                np.random.randint(input_cshape[1]+16, self.sim_shape[1]/cratio - input_cshape[1] - 16),
                np.random.randint(input_cshape[2]+16, self.sim_shape[2]/cratio - input_cshape[2] - 16)]
    cstate_subdomain = SubDomain(rand_pos, input_cshape)

    # get state subdomain and geometry_subdomain
    state_subdomain = state_shape_converter.out_in_subdomain(copy(cstate_subdomain))

    # get seq state subdomain
    seq_state_subdomain = seq_state_shape_converter.out_in_subdomain(copy(cstate_subdomain))

    # download data
    self.download_datapoint(state_subdomain, ind, encode_state, encode_boundary)
    for i in xrange(seq_length):
      self.download_datapoint(seq_state_subdomain, ind+i, encode_state, encode_boundary)

    # data point and return it
    return DataPoint(ind, seq_length, state_subdomain, seq_state_subdomain)

  def generate_rand_cdp(self, seq_length, state_shape_converter, seq_state_shape_converter, input_cshape, cratio, encode_state, encode_boundary):
    # select random index
    ind = np.random.randint(0, (5024/self.step_ratio)-seq_length)

    # select random pos to grab from data
    rand_pos = [np.random.randint(input_cshape[0]+16, self.sim_shape[0]/cratio - input_cshape[0] - 16),
                np.random.randint(input_cshape[1]+16, self.sim_shape[1]/cratio - input_cshape[1] - 16),
                np.random.randint(input_cshape[2]+16, self.sim_shape[2]/cratio - input_cshape[2] - 16)]
    cstate_subdomain = SubDomain(rand_pos, input_cshape)

    # get state subdomain and geometry_subdomain
    state_subdomain = state_shape_converter.out_in_subdomain(copy(cstate_subdomain))

    # get seq state subdomain
    seq_state_subdomain = seq_state_shape_converter.out_in_subdomain(copy(cstate_subdomain))

    # download data and compress
    self.download_state(state_subdomain, ind)
    state = self.read_state(ind, state_subdomain, add_batch=True, return_padding=True)
    cstate = encode_state({'state':state})[0]
    np.save(self.iter_to_cstate_filename(ind + i, state_subdomain), cstate)
    os.remove(self.iter_to_state_filename(ind + i, state_subdomain))
    for i in xrange(seq_length)
      self.download_state(seq_state_subdomain, ind + i)
      state = self.read_state(ind + i, seq_state_subdomain, add_batch=True, return_padding=True)
      cstate = encode_state({'state':state})[0]
      np.save(self.iter_to_cstate_filename(ind + i, seq_state_subdomain), cstate)
      os.remove(self.iter_to_state_filename(ind + i, seq_state_subdomain))

    # data point and return it
    return DataPoint(ind, seq_length, state_subdomain, seq_state_subdomain)

class DataPoint:

  def __init__(self, ind, seq_length, state_subdomain, seq_state_subdomain):
    self.ind = ind
    self.seq_length = seq_length
    self.state_subdomain = state_subdomain
    self.seq_state_subdomain = seq_state_subdomain

  def to_string(self):
    string  = ''
    string += str(self.ind) + ','
    string += str(self.seq_length) + ','
    for p in self.state_subdomain.pos:
      string += str(p) + ','
    for s in self.state_subdomain.size:
      string += str(s) + ','
    for p in self.seq_state_subdomain.pos:
      string += str(p) + ','
    for s in self.seq_state_subdomain.size:
      string += str(s) + ','
    string += '\n'
    return string

  def load_string(self, string):
    values = string.split(',')[:-1]
    values = [int(x) for x in values]
    self.ind = values.pop(0)
    self.seq_length = values.pop(0)
    dims = len(values)/4
    self.state_subdomain = SubDomain([values[0], values[1], values[2]], 
                                     [values[3], values[4], values[5]])
    self.seq_state_subdomain = SubDomain([values[6], values[7], values[8]], 
                                         [values[9], values[10], values[11]])

