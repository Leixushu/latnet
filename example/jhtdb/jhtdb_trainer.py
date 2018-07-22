#!/usr/bin/env python

import sys
import os
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# import latnet
sys.path.append('../../latnet')
from domain import Domain
from trainer import Trainer
from controller import LatNetController
from network_architectures.standard_network import StandardNetwork
import utils.binvox_rw as binvox_rw
import numpy as np
import cv2
import glob

class FakeDomain(Domain):
  name = "JHTDB"
  num_simulations = 5
  periodic_x = True
  periodic_y = True
  periodic_z = True

class JHTDBSimulation(Trainer):
  script_name = __file__
  network = StandardNetwork
  domains = [FakeDomain]

  @classmethod
  def update_defaults(cls, defaults):
    defaults.update({
        'train_sim_dir': './train_data',
        'latnet_network_dir': './network_save',
        'input_cshape': '8x8x8',
        #'input_cshape': '16x16x16',
        'nr_downsamples': 2,
        'filter_size': 16,
        'filter_size_compression': 16,
        'nr_residual_compression': 2,
        'nr_residual_encoder': 1,
        'train_autoencoder': False,
        'start_num_data_points_train': 50,
        'seq_length': 5,
        #'batch_size': 32,
        'batch_size': 16,
        'max_queue': 400,
        'DxQy': 'D3Q4'})

if __name__ == '__main__':
  sim = LatNetController(trainer=JHTDBSimulation)
  sim.run()
