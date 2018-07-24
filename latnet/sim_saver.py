
import lattice

import numpy as np
import psutil as ps
import os
import glob

class SimSaver(object):

  def __init__(self, config):
    self.save_dir = config.sim_dir
    self.save_format = config.save_format
    self.save_cstate = config.save_cstate
    self.DxQy = lattice.TYPES[config.DxQy]
    self.sim_restore_iter = config.sim_restore_iter
    self.lb_to_ln = config.lb_to_ln

    self.latnet_files = []

  @classmethod
  def add_options(cls, group):
    group.add_argument('--sim_dir', 
                   help='where to save network generated simulation', 
                   type=str,
                   default='./simulation')
    group.add_argument('--sim_save_every', 
                   help='how often to save compressed state of simulation', 
                   type=int,
                   default=4)
    group.add_argument('--save_format', 
                   help='format to save compressed state', 
                   type=str,
                   choices=['npy'],
                   default='npy')
    group.add_argument('--train_cshape', 
                   help='size of data to train on', 
                   type=str,
                   default='16x16')

  def iter_to_filename(self, iteration, with_format=False):
    file_name = self.save_dir + '/' + str(iteration).zfill(6) + ".cpoint"
    if with_format and (self.save_format == 'npy'):
      file_name += ".npz"
    elif with_format and (self.save_format == 'vtk'):
      file_name += ".vti"
    return file_name

  def save(self, iteration, vel, rho, cstate):
    if self.save_format == 'npy':
      self.save_numpy(iteration, vel, rho, cstate)
    elif self.save_format == 'vtk':
      # TODO add vtk save method
      print("vtk save formate not implemented yet")
      exit()

  def save_numpy(self, iteration, vel, rho, cstate):
    file_name = self.iter_to_filename(iteration)
    if self.save_cstate:
      np.savez(file_name, vel=vel, rho=rho, cstate=cstate)
    else:
      np.savez(file_name, vel=vel, rho=rho)
    self.latnet_files.append(file_name)

  def read_vel_rho(self, iteration, subdomain=None, add_batch=False):
    if self.save_format == 'npy':
      vel, rho, _ = self.load_numpy(iteration)
    if not add_batch:
      vel = vel[0]
      rho = rho[0]
    return vel, rho

  def load_numpy(self, iteration):
    file_name = self.iter_to_filename(iteration, with_format=True)
    save_file = np.load(file_name)
    vel = save_file.f.vel
    rho = save_file.f.rho
    if self.save_cstate:
      cstate = save_file.f.cstate
    else:
      cstate = None
    return vel, rho, cstate

