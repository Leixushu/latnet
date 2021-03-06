
# LatNet (Beta Release)

[![IMAGE ALT TEXT HERE](http://img.youtube.com/vi/v6Fwxodi3dk/0.jpg)](https://www.youtube.com/watch?v=v6Fwxodi3dk)

A library for performing Lattice Boltzmann fluid simulations using neural networks. A paper going over the method can be found [here](https://arxiv.org/abs/1705.09036). The original source code for the paper can also be found [here](https://github.com/loliverhennigh/Phy-Net). This library represents an extension of the original work and is designed to handle large scale simulations. This is a beta release and does not contain all the desired features and has untested functionality. The library uses TensorFlow for the neural networks and Sailfish to generate the fluid simulations.

# Getting Started

## Sailfish Library

LatNet uses the [Sailfish](http://sailfish.us.edu.pl/) to generate the fluid simulations. Sailfish requires a GPU and CUDA to run. Installing CUDA can be specific to your system and GPU but we recommend installing it in the way [TensorFlow suggests](https://www.tensorflow.org/install/install_linux#nvidia_requirements_to_run_tensorflow_with_gpu_support). You will also need the following packages,

`
apt-get install python-pycuda python-numpy python-matplotlib python-scipy python-sympy
apt-get install python-zmq python-execnet git
`

To obtain the Sailfish library run,

`
./setup_sailfish.sh
`

There are multiple forks of Sailfish and this version was tested with Python 2.7 and a GTX 1080 GPU with CUDA 8.0. We tested on CUDA 9.0 and there appear to be no problems.

## Train Network

To run the network reported in the original paper, move to the `example/channel` directory and run

`
python standard_network_trainer.py
`

This will generate a train set of simulations and requires around 50 GBs of memory. Training should require around 12 hours. The network is saved in the directory `network_save` and you can monitor progress with TensorBoard.

There are many parameters you can change for training such as using Generative Adversarial Loss and multiple GPUs. To get a complete list of parameters run with `--help` flag.

## Evaluate Network

Once the network is trained to reasonable performance you evaluate in by running

`
python standard_network_eval.py
`

This will generate a video comparing the generated simulation to the original in the `figs` directory and save all the data in the `simulation` directory.

# Improvements on Previous Work

* Pressure and Velocity boundary conditions. Forcing term are also implemented but the force needs to be constant for train and test set.

* Generative Adversarial Training as seen [here](https://arxiv.org/pdf/1801.09710.pdf).

* Arbitrary sized simulations for train set.

* Dynamic Train set allowing simulations to be generated while training network.

* Multi-GPU training.

* Running simulations on CPU ram instead of GPU dram allowing for much larger simulations to be generated (1,000 by 1,000 by 1,000 grid cells with only 32 GB of CPU ram).

* New network architectures.

* New domains such as lid driven cavity and isotropic turbulence.

* Data augmentation such as flipping and rotating simulation.

* Active Learning. New data is dynamically added to the train set while training. The added data is ment to fool and network and make it more rebust. This appears to greatly stabalize training and improve model.

# Future Improvements

These are the features with priority that will be released in future versions.

* 3D simulations. (Currently available in development branch `john_hopkins`)

* Physically inspired network architecture. (Some already available such as `LESNet` and `generalized_lb` however these are untested and working a progress)

* Add other non-Lattice Boltzmann solvers. (Currently available in development branch `john_hopkins` where latnet can be trained on john hopkins turbulence dataset) 


