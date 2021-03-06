
"""functions used to construct different architectures  
"""

import tensorflow as tf
import tensorflow.contrib.layers as tcl
import numpy as np

FLAGS = tf.app.flags.FLAGS

def int_shape(x):
  return list(map(int, x.get_shape()))

def leaky_relu(x, leak=0.1):
  f1 = 0.5 * (1 + leak)
  f2 = 0.5 * (1 - leak)
  return f1 * x + f2 * abs(x)

def selu(x):
  with tf.variable_scope('elu') as scope:
    alpha = 1.6732632423543772848170429916717
    scale = 1.0507009873554804934193349852946
    return scale*tf.where(x>=0.0, x, alpha*tf.nn.elu(x))

def concat_elu(x):
  """ like concatenated ReLU (http://arxiv.org/abs/1603.05201), but then with ELU """
  axis = len(x.get_shape())-1
  return tf.nn.elu(tf.concat([x, -x], axis))

def concat_relu(x):
  axis = len(x.get_shape())-1
  return tf.nn.relu(tf.concat([x, -x], axis))

def hard_sigmoid(x):
  return tf.minimum(1.0, tf.maximum(0.00, x + 0.5))   

def triangle_wave(x):
  y = 0.0
  for i in xrange(3):
    y += (-1.0)**(i) * tf.sin(2.0*np.pi*(2.0*i+1.0)*x)/(2.0*i+1.0)**(2)
  y = 0.5 * (8/(np.pi**2) * y) + .5
  return y

def tanh(x):
  return tf.nn.tanh(x)

def set_nonlinearity(name):
  if name == 'concat_elu':
    return concat_elu
  elif name == 'elu':
    return tf.nn.elu
  elif name == 'concat_relu':
    return tf.nn.crelu
  elif name == 'relu':
    return tf.nn.relu
  elif name == 'concat_relu':
    return concat_relu
  elif name == 'selu':
    return selu
  elif name == 'leaky_relu':
    return leaky_relu
  elif name == 'sigmoid':
    return tf.nn.sigmoid
  elif name == 'hard_sigmoid':
    return hard_sigmoid
  elif name == 'tanh':
    return tanh
  else:
    raise('nonlinearity ' + name + ' is not supported')

def _activation_summary(x):
  """Helper to create summaries for activations.

  Creates a summary that provides a histogram of activations.
  Creates a summary that measure the sparsity of activations.

  Args:
    x: Tensor
 Returns:
    nothing
  """
  tensor_name = x.op.name
  with tf.device('/cpu:0'):
    tf.summary.histogram(tensor_name + '/activations', x)
    tf.summary.scalar(tensor_name + '/sparsity', tf.nn.zero_fraction(x))

def _variable(name, shape, initializer):
  """Helper to create a Variable.
  Args:
    name: name of the variable
    shape: list of ints
    initializer: initializer for Variable
  Returns:
    Variable Tensor
  """
  # getting rid of stddev for xavier ## testing this for faster convergence
  #initializer = tf.random_normal_initializer(stddev=0.0000001)
  var = tf.get_variable(name, shape, initializer=initializer)
  _activation_summary(var)
  return var

def simple_conv_2d(x, k):
  """A simplified 2D convolution operation"""
  y = tf.nn.conv2d(x, k, [1, 1, 1, 1], padding='VALID')
  return y

def simple_conv_3d(x, k):
  """A simplified 3D convolution operation"""
  y = tf.nn.conv3d(x, k, [1, 1, 1, 1, 1], padding='VALID')
  return y

def conv_layer(x, kernel_size, stride, filter_size, name, nonlinearity=None, normalize=None, phase=None):
  with tf.variable_scope(name) as scope:
    input_channels = x.get_shape()[-1]
 
    # determine dim
    length_input = len(x.get_shape()) - 2
    if length_input not in [2, 3]:
      print("conv layer does not support non 2d or 3d inputs")
      exit()

    weights = _variable('weights', shape=length_input*[kernel_size] + [input_channels,filter_size],initializer=tf.contrib.layers.xavier_initializer_conv2d())
    biases = _variable('biases',[filter_size],initializer=tf.constant_initializer(0.0))

    if length_input == 2:
      conv = tf.nn.conv2d(x, weights, strides=[1, stride, stride, 1], padding='VALID')
    elif length_input == 3:
      conv = tf.nn.conv3d(x, weights, strides=[1, stride, stride, stride, 1], padding='VALID')

    conv = tf.nn.bias_add(conv, biases)

    # normalize
    if normalize == "batch_norm":
      conv = tf.layers.batch_normalization(conv, training=True, momentum=0.9)
    elif normalize == "layer_norm":
      conv = tcl.layer_norm(conv)

    # apply nonlinearity
    if nonlinearity is not None:
      conv = nonlinearity(conv)
    return conv

def mimic_conv_pad(x, kernel_size, stride):
  if stride == 2:
    x = max_pool(x)
  edge_cut = (kernel_size-1)/2
  x = trim_tensor(x, edge_cut)
  return x

def mimic_trans_conv_pad(x, kernel_size, stride):
  if stride == 2:
    x = upsampleing_resize(x)
  edge_cut = (kernel_size-1)/2
  x = trim_tensor(x, edge_cut)
  return x

def mimic_res_pad(x, kernel_size, stride):
  edge_cut = (kernel_size-1)/2
  x = trim_tensor(x, edge_cut)
  if stride == 2:
    x = max_pool(x)
  x = trim_tensor(x, edge_cut)
  return x

def apply_pad(x, pad):
  x = x * (1.0 - pad)
  return x

def simple_trans_conv_2d(x, k):
  """A simplified 2D trans convolution operation"""
  output_shape = tf.stack([tf.shape(x)[0], tf.shape(x)[1], tf.shape(x)[2], tf.shape(k)[2]]) 
  y = tf.nn.conv2d_transpose(x, k, output_shape, [1, 1, 1, 1], padding='SAME')
  y = tf.reshape(y, [int(x.get_shape()[0]), int(x.get_shape()[1]), int(x.get_shape()[2]), int(k.get_shape()[2])])
  return y


def simple_trans_conv_2d(x, k):
  """A simplified 2D trans convolution operation"""
  output_shape = tf.stack([tf.shape(x)[0], tf.shape(x)[1], tf.shape(x)[2], tf.shape(k)[2]]) 
  y = tf.nn.conv2d_transpose(x, k, output_shape, [1, 1, 1, 1], padding='SAME')
  y = tf.reshape(y, [int(x.get_shape()[0]), int(x.get_shape()[1]), int(x.get_shape()[2]), int(k.get_shape()[2])])
  return y

def simple_trans_conv_3d(x, k):
  """A simplified 3D trans convolution operation"""
  output_shape = tf.stack([tf.shape(x)[0], tf.shape(x)[1], tf.shape(x)[2], tf.shape(x)[3], tf.shape(k)[3]]) 
  y = tf.nn.conv3d_transpose(x, k, output_shape, [1, 1, 1, 1, 1], padding='SAME')
  y = tf.reshape(y, [int(x.get_shape()[0]), int(x.get_shape()[1]), int(x.get_shape()[2]), int(x.get_shape()[3]), int(k.get_shape()[3])])
  return y

def transpose_conv_layer(x, kernel_size, stride, filter_size, name, nonlinearity=None):
  with tf.variable_scope(name) as scope:
    input_channels = x.get_shape()[-1]
     
    # determine dim
    length_input = len(x.get_shape()) - 2
    batch_size = tf.shape(x)[0]
    if length_input not in [2, 3]:
      print("transpose conv layer does not support non 2d or 3d inputs")
      exit()

    weights = _variable('weights', shape=length_input*[kernel_size] + [filter_size,input_channels],initializer=tf.contrib.layers.xavier_initializer_conv2d())
    biases = _variable('biases',[filter_size],initializer=tf.constant_initializer(0.0))
    batch_size = tf.shape(x)[0]

    if length_input == 2:
      output_shape = tf.stack([tf.shape(x)[0], tf.shape(x)[1]*stride, tf.shape(x)[2]*stride, filter_size]) 
      conv = tf.nn.conv2d_transpose(x, weights, output_shape, strides=[1,stride,stride,1], padding='SAME')
    elif length_input == 3:
      output_shape = tf.stack([tf.shape(x)[0], tf.shape(x)[1]*stride, tf.shape(x)[2]*stride, tf.shape(x)[3]*stride, filter_size]) 
      conv = tf.nn.conv3d_transpose(x, weights, output_shape, strides=[1,stride,stride,stride,1], padding='SAME')

    conv = tf.nn.bias_add(conv, biases)
    if nonlinearity is not None:
      conv = nonlinearity(conv)

    #reshape (transpose conv causes output to have ? size)
    #shape = int_shape(x)
    if  length_input == 2:
      conv = conv[:,1:-1,1:-1]
      pass
      #conv = tf.reshape(conv, [shape[0], shape[1]*stride, shape[2]*stride, filter_size])
    if  length_input == 3:
      conv = conv[:,1:-1,1:-1,1:-1]
      pass
      #conv = tf.reshape(conv, [shape[0], shape[1]*stride, shape[2]*stride, shape[3]*stride, filter_size])
      #conv = conv[:,2:-2,2:-2,2:-2]
    return conv

def fc_layer(x, hiddens, name, nonlinearity=None, flat = False):
  with tf.variable_scope(name) as scope:
    input_shape = tf.shape(x)
    if flat:
      dim = input_shape[1]*input_shape[2]*input_shape[3]
      inputs_processed = tf.reshape(x, [-1,dim])
    else:
      dim = input_shape[1]
      inputs_processed = x 
   
    dim = 100 
    weights = _variable('weights', shape=[dim,hiddens],initializer=tf.contrib.layers.xavier_initializer())
    biases = _variable('biases', [hiddens], initializer=tf.contrib.layers.xavier_initializer())
    output = tf.add(tf.matmul(inputs_processed,weights),biases,name=name)
    if nonlinearity is not None:
      output = nonlinearity(output)
    return output

def nin(x, num_units, idx):
    """ a network in network layer (1x1 CONV) """
    x = conv_layer(x, 1, 1, num_units, idx)
    return x

def downsample(x, sampling="avg"):
  if sampling == "avg":
    x = avg_pool(x)
  elif sampling == "max":
    x = max_pool(x)
  return x

def upsampleing_resize(x):
  x_shape = tf.shape(x)
  x = tf.image.resize_nearest_neighbor(x, [2*x_shape[1], 2*x_shape[2]])
  return x

def avg_pool(x):
  length_input = len(x.get_shape()) - 2
  if length_input == 2:
    x = tf.nn.avg_pool(x, [1,2,2,1], [1,2,2,1], padding='VALID')
  if length_input == 3:
    x = tf.nn.avg_pool3d(x, [1,2,2,2,1], [1,2,2,2,1], padding='VALID')
  return x

def max_pool(x):
  length_input = len(x.get_shape()) - 2
  if length_input == 2:
    x = tf.nn.max_pool(x, [1,2,2,1], [1,2,2,1], padding='VALID')
  if length_input == 3:
    x = tf.nn.max_pool3d(x, [1,2,2,2,1], [1,2,2,2,1], padding='VALID')
  return x

def trim_tensor(x, trim):
  length_input = len(x.get_shape()) - 2
  if length_input == 2:
    x = x[:,trim:-trim, trim:-trim]
  if length_input == 3:
    x = x[:,trim:-trim, trim:-trim, trim:-trim]
  return x

def res_block(x, a=None, 
              filter_size=16, 
              kernel_size=3, 
              nonlinearity=concat_elu, 
              keep_p=1.0, stride=1, 
              gated=True, name="resnet", 
              begin_nonlinearity=True, 
              phase=None,
              normalize=None):
            
  # determine if 2d or 3d trans conv is needed
  length_input = len(x.get_shape())

  orig_x = x
  if (normalize == "batch_norm") and begin_nonlinearity:
    x = tf.layers.batch_normalization(x, training=True, momentum=0.9)
  elif (normalize == "layer_norm") and begin_nonlinearity:
    x = tcl.layer_norm(x)
  if begin_nonlinearity: 
    x = nonlinearity(x) 
  if stride == 1:
    x = conv_layer(x, kernel_size, stride, filter_size, name + '_conv_1')
    edge_cut = ((kernel_size-1)/2)
    orig_x = trim_tensor(orig_x, edge_cut)
  elif stride == 2:
    x = conv_layer(x, 4, stride, filter_size, name + '_conv_1')
    if length_input == 4:
      orig_x = tf.nn.avg_pool(orig_x, [1,4,4,1], [1,2,2,1], padding='VALID')
    elif length_input == 5:
      orig_x = tf.nn.avg_pool3d(orig_x, [1,4,4,4,1], [1,2,2,2,1], padding='VALID')
  else:
    print("stride > 2 is not supported")
    exit()
  if a is not None:
    shape_a = int_shape(a) 
    shape_x_1 = int_shape(x)
    if length_input == 4:
      a = tf.pad(
        a, [[0, 0], [0, shape_x_1[1]-shape_a[1]], [0, shape_x_1[2]-shape_a[2]],
        [0, 0]])
    elif length_input == 5:
      a = tf.pad(
        a, [[0, 0], [0, shape_x_1[1]-shape_a[1]], [0, shape_x_1[2]-shape_a[2]], [0, shape_x_1[3]-shape_a[3]],
        [0, 0]])
    x += nin(nonlinearity(a), filter_size, name + '_nin')
  if normalize == "batch_norm":
    #x = tcl.batch_norm(x,  is_training=phase,center=True, scale=True)
    x = tf.layers.batch_normalization(x, training=True, momentum=0.9)
  elif normalize == "layer_norm":
    x = tcl.layer_norm(x)
  x = nonlinearity(x)
  #if keep_p < 1.0:
  #  x = tf.nn.dropout(x, keep_prob=keep_p)
  if not gated:
    #pass
    x = conv_layer(x, kernel_size, 1, filter_size, name + '_conv_2')
    edge_cut = ((kernel_size-1)/2)
    orig_x = trim_tensor(orig_x, edge_cut)
  else:
    x = conv_layer(x, kernel_size, 1, filter_size*2, name + '_conv_2')
    edge_cut = ((kernel_size-1)/2)
    orig_x = trim_tensor(orig_x, edge_cut)
    x_1, x_2 = tf.split(x,2,length_input-1)
    x = x_1 * tf.nn.sigmoid(x_2)

  # pad it
  out_filter = filter_size
  in_filter = int(orig_x.get_shape()[-1])
  if out_filter > in_filter:
    if length_input == 4:
      orig_x = tf.pad(
          orig_x, [[0, 0], [0, 0], [0, 0],
          [(out_filter-in_filter), 0]])
    elif length_input == 5:
      orig_x = tf.pad(
          orig_x, [[0, 0], [0, 0], [0, 0], [0, 0],
          [(out_filter-in_filter), 0]])
  elif out_filter < in_filter:
    orig_x = nin(orig_x, out_filter, name + '_nin_pad')

  x = orig_x + x
  return x

def fast_conv_layer(x, kernel_size, stride, filter_size, filter_size_conv, name):
  conv_x = x[...,0:filter_size_conv]
  conv_x = conv_layer(conv_x, kernel_size, stride, filter_size_conv, name + '_kernel')
  edge_cut = ((kernel_size-1)/2)
  x = x[:,edge_cut:-edge_cut,edge_cut:-edge_cut,filter_size_conv:]
  x = tf.concat([conv_x, x], axis=-1)
  x = conv_layer(x, 1, 1, filter_size, name + '_nin')
  return x

def fast_res_block(x, a=None, 
              filter_size=16,
              filter_size_conv=4,
              kernel_size=7, 
              nonlinearity=concat_elu, 
              name="resnet", 
              begin_nonlinearity=True, 
              normalize=None):
            
  # determine if 2d or 3d trans conv is needed
  length_input = len(x.get_shape())

  orig_x = x
  if begin_nonlinearity: 
    x = nonlinearity(x) 
  x = fast_conv_layer(x, kernel_size, 1, filter_size, filter_size_conv, name + '_conv_1')
  edge_cut = ((kernel_size-1)/2)
  orig_x = orig_x[:,edge_cut:-edge_cut,edge_cut:-edge_cut]
  x = nonlinearity(x)

  x = fast_conv_layer(x, kernel_size, 1, filter_size, filter_size_conv, name + '_conv_2')
  edge_cut = ((kernel_size-1)/2)
  orig_x = orig_x[:,edge_cut:-edge_cut,edge_cut:-edge_cut]

  # pad it
  out_filter = int(x.get_shape()[-1])
  in_filter = int(orig_x.get_shape()[-1])
  if out_filter > in_filter:
    if length_input == 4:
      orig_x = tf.pad(
          orig_x, [[0, 0], [0, 0], [0, 0],
          [(out_filter-in_filter), 0]])
    elif length_input == 5:
      orig_x = tf.pad(
          orig_x, [[0, 0], [0, 0], [0, 0], [0, 0],
          [(out_filter-in_filter), 0]])
  elif out_filter < in_filter:
    orig_x = nin(orig_x, out_filter, name + '_nin_pad')

  x = orig_x + x
  return x



