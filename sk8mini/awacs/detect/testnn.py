'''
testnn.py
takeoff from testsamsonzhang.py

python3 -Wi::DeprecationWarning testnn.py --task classify --iimage 8jdig0.png --display
'''

import numpy as np
from matplotlib import pyplot as plt
import json
import cv2
import argparse
import logging
import nn

gargs = None

def prepTrainingData(fname):
	# input data into np array
	import pandas as pd
	data = pd.read_csv(fname)
	data = np.array(data)
	m, n = data.shape
	print(data.shape)
	
	np.random.shuffle(data) # shuffle 
	
	# split into training and validation, normalize to 0:1
	data_dev = data[0:1000].T
	Y_dev = data_dev[0]
	X_dev = data_dev[1:n]
	X_dev = X_dev / 255.
	
	data_train = data[1000:m].T
	Y_train = data_train[0]
	X_train = data_train[1:n]
	X_train = X_train / 255.
	_,m_train = X_train.shape

	return X_train, Y_train, m

def train(data, alpha, epochs):
	X_train, Y_train, m = prepTrainingData(data)
	print(X_train.shape, Y_train.shape, m)

	# train
	W1, b1, W2, b2 = nn.gradient_descent(X_train, Y_train, alpha, epochs, m)

	# save model
	model = {
		'W1': W1,
		'b1': b1,
		'W2': W2,
		'b2': b2
	}


	# the input layer has 784 numbers
	# the hidden layer has 10 neurons ?
	# the output layer has 10 neurons - one for each cls
#	initModel([10,10])
	return model

## model is a python list of numpy.arrays
#def initModel(sizeOfEachLayer):
#	for sizeOfEachLayer
#		model = []
#		return model

def classify(X,y, W1, b1, W2, b2):
	prediction = nn.make_predictions(X, W1, b1, W2, b2)
	print(f'Prediction: {prediction},  truth: {y}')
	
	if gargs.display:
		current_image = X.reshape((28,28)) * 255
		plt.gray()
		plt.imshow(current_image, interpolation='nearest')
		plt.show()

def writeModel(fname, model):
	model['W1'] = model['W1'].tolist()
	model['b1'] = model['b1'].tolist()
	model['W2'] = model['W2'].tolist()
	model['b2'] = model['b2'].tolist()

	with open(fname, 'w') as f:
		f.write(json.dumps(model))

def readModel(fname):
	with open(fname, 'r') as f:
		model = json.loads(f.read())

	model['W1'] = np.array(model['W1'])
	model['b1'] = np.array(model['b1'])
	model['W2'] = np.array(model['W2'])
	model['b2'] = np.array(model['b2'])
	return model

def preprocess(idir, fname):
	y = fname[0]  # first char of the filename is the cls index
	y = int(y)
	img = cv2.imread(idir + fname)
	img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	#X = np.concatenate(img)  # flatten tile to row
	X = img.reshape((784,1))
	X = (255 - X)  # invert b/w
	X = X / 255    # normalize
	return X,y

def getArguments():
	# file inputs
	parser = argparse.ArgumentParser()
	parser.add_argument('-t'  ,'--task'      ,default='classify'   ,choices=['classify','train'] ,help='task: train or classify'		)
	parser.add_argument('-id' ,'--idir'      ,default='photos/jdig/single/'                      ,help='input folder'			)
	parser.add_argument('-m'  ,'--imodel'    ,default='model.json'                               ,help='input model file'			)
	parser.add_argument('-td' ,'--itraindata',default='train.csv'                                ,help='input training data'		)
	parser.add_argument('-im' ,'--iimage'    ,default='0jdig0.png'                               ,help='input image for classification'	)
                                                                       
	# net definition
	parser.add_argument('-ni' ,'--numinputs' ,default=784          ,type=int                     ,help='number of inputs'			)
	parser.add_argument('-wd' ,'--widths'    ,default=[10,10]      ,nargs='*',type=int           ,help='width of each layer'		)
	parser.add_argument('-af' ,'--activates' ,default=[0,2]        ,nargs='*',type=int           ,help='0:relu, 1:sigmoid, 2:softmax'	)
	parser.add_argument('-nm' ,'--nonmaxima' ,default=True         ,action='store_true'          ,help='non-maxima suppression'		)
                                                                       
	# training specs
	parser.add_argument('-ne' ,'--numepochs' ,default=500          ,type=int                     ,help='number of inputs'			)
	parser.add_argument('-al' ,'--alpha'     ,default=.10          ,type=int                     ,help='number of inputs'			)

	# logging options                                              
	parser.add_argument('-v'  ,'--verbose'   ,default=False        ,action='store_true'          ,help='display additional logging'		)
	parser.add_argument('-q'  ,'--quiet'     ,default=False        ,action='store_true'          ,help='suppresses all output'		)
	parser.add_argument('-d'  ,'--display'   ,default=False        ,action='store_true'          ,help='display the input image'		)

	args = parser.parse_args()	# returns Namespace object, use dot-notation
	return args

def setupLogging(debug,quiet):
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if gargs.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if gargs.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(gargs)

def main():
	global gargs
	gargs = getArguments()
	setupLogging(gargs.verbose, gargs.quiet)

	if gargs.task == 'train':
		model = train(gargs.idir + gargs.itraindata, gargs.alpha, gargs.numepochs)
		writeModel(gargs.idir + gargs.imodel, model)
	elif gargs.task == 'classify':
		model = readModel(gargs.idir + gargs.imodel)
		X,y = preprocess(gargs.idir, gargs.iimage)
		classify(X, y, model['W1'], model['b1'], model['W2'], model['b2'])

if __name__ == '__main__':
	main()
