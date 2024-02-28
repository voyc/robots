'''
nn.py - library of neural net functions
see samsonzhang.py
'''

import numpy as np
import copy
import json
import yaml
import logging

import time
start = 0
end = 0

#---------- config management --------------

config = {  
	"model": "photos/jdig/single/model.json",
	"train": "photos/jdig/single/train.csv",
	"folder": "photos/jdig/single/",
	"image": "0jdig0",
	"widths": [784,10,10],
	"activates": [0, 0, 2],
	"nonmaxima": 1,
	"epochs": 500,
	"alpha": 0.1
}

def readConfig(fname):
	global config
	with open(fname, 'r') as file:
		config = yaml.safe_load(file)

#---------- model management --------------

model = []

def fixModel():
	global model

	vmin = -0.5
	vmax = 0.5
	step = 0.011
	way = 1
	latest = .1

	def getSpray():
		nonlocal way, latest

		latest = latest + (way * step)
		
		if way > 0 and latest + step >= vmax:
			way = way * -1	
		elif way < 0 and latest - step <= vmin:
			way = way * -1	
		return latest

	[W,b] = model

	for n in range(0,len(b[1])): b[1][n] = getSpray()
	for n in range(0,len(b[2])): b[2][n] = getSpray()

	m,n = W[1].shape
	for i in range(m):
		for j in range(n):
			W[1][i][j] = getSpray()
	m,n = W[2].shape
	for i in range(m):
		for j in range(n):
			W[2][i][j] = getSpray()
	model = [W, b]

def initModel():
	global model
	W = [np.array([0])]
	b = [np.array([0])]
	w = config['widths']
	for n in range(1, len(w)):
		W.append(np.random.rand(w[n], w[n-1]) - 0.5)
		b.append(np.random.rand(w[n], 1) - 0.5)
	model = [W, b]

def readModel():
	global model
	with open(config['model'], 'r') as f:
		flatmodel = json.loads(f.read())

	[W, b] = flatmodel
	numlayers = len(W)
	for n in range(0, numlayers):
		W[n] = np.array(W[n])
		b[n] = np.array(b[n])
	model = [W,b]

def writeModel():
	flatmodel = copy.deepcopy(model)  # slow and unnecessary because it happens once after training
	[W, b] = flatmodel
	for n in range(0, len(W)):
		W[n] = W[n].tolist()
		b[n] = b[n].tolist()

	with open(config['model'], 'w') as f:
		f.write(json.dumps(flatmodel))

#---------- activation functions ----------

def activate(code, value):
	if code == 0:
		activated = ReLU(value)
	elif code == 1:
		activated = sigmoid(value)
	elif code == 2:
		activated = softmax(value)
	return activated

def deactivate(code, value):
	if code == 0:
		deactivated = ReLU_deriv(value)
	elif code == 1:
		deactivated = sigmoid_deriv(value)
	elif code == 2:
		deactivated = softmax_deriv(value)   # ????
	return activated

def ReLU(Z):
	# rectified linear unit
	return np.maximum(Z, 0)

def ReLU_deriv(Z):
	return Z > 0

def softmax(Z):
	# turn an array of numbers into a probability distribution
	A = np.exp(Z) / sum(np.exp(Z))
	return A

#---------- data prep -------------------

def prepTrainingData():
	import pandas as pd
	data = pd.read_csv(config['train'])
	data = np.array(data)
	m, n = data.shape   # (m cols: num samples, n rows: inputs per sample)
	logging.info(f'training data: {data.shape}')
	
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

	return X_train, Y_train, m # m_train

#---------- data prep: encoding -------------------

def oneHotEncode(A):
	# encode categorical value to numerical, ie 3 or 'cat' to [0,0,0,1,0,0,0,0]
	# https://machinelearningmastery.com/one-hot-encoding-for-categorical-data/
	one_hot = np.zeros((A.size, A.max() + 1))  # 2D array (41000,10)
	one_hot[np.arange(A.size), A] = 1
	one_hot = one_hot.T # transpose rows and columns 
	return one_hot

def oneHotDecode(A):
	return np.argmax(A, 0)

#---------- propagation -------------------

def forward(X):
	[W, b] = model
	numlayers = len(W)
	Z = [0] * numlayers  # empty 0 layer, plus multiple computed layers
	A = [0] * numlayers  # 0 layer has input, plus multiple computed layers 
	A[0] = X   # if we ever write to A[0] it will clobber input X
	act = config['activates']
	for n in range(1, numlayers):
		Z[n] = W[n].dot(A[n-1]) + b[n]  # wx + b
		A[n] = activate(act[n], Z[n]) 
	return Z, A

def backward( Z, A, X, Y, m):
	[W,_] = model   # input, no update yet
	numlayers = len(model[0])
	dZ = [0] * numlayers
	dW = [0] * numlayers
	db = [0] * numlayers
	one_hot_Y = oneHotEncode(Y)
	for n in range(numlayers-1, 0, -1):  # 2,1
		if n == numlayers-1:   # output layer
			dZ[n] = A[n] - one_hot_Y          # reverse the softmax activation function
			dW[n] = 1 / m * dZ[n].dot(A[n-1].T)  # reverse the previous layer's dot product
			db[n] = 1 / m * np.sum(dZ[n])

		if n == 1:  
			dZ[n] = W[n+1].T.dot(dZ[n+1]) * ReLU_deriv(Z[n])  # reverse the activation
			dW[n] = 1 / m * dZ[n].dot(X.T)            # using X instead of A[n-1]
			db[n] = 1 / m * np.sum(dZ[n])

		#dZ = W2.T.dot(dZ2) * ReLU_deriv(Z1)  # reverse the activation
		#dW = 1 / m * dZ1.dot(X.T)            # using X instead of A[n-1]
		#db = 1 / m * np.sum(dZ1)

	return dW, db

def updateModel(dW, db, alpha):
	global model
	[W,b] = model
	numlayers = len(model[0])
	for n in range(1, numlayers):
		W[n] = W[n] - alpha * dW[n]
		b[n] = b[n] - alpha * db[n]

def get_predictions(A):
	return np.argmax(A, 0)

def get_accuracy(predictions, Y):
	return np.sum(predictions == Y) / Y.size

def gradient_descent(X, Y, alpha, epochs, m):
	global start, end
	for i in range(epochs):
		start = time.time()
		Z, A = forward(X)
		dW, db = backward( Z, A, X, Y, m)
		updateModel(dW, db, alpha)
		end = time.time()
		if i % 10 == 0:
			numlayers = len(model[0])
			predictions = get_predictions(A[numlayers-1])
			accuracy = get_accuracy(predictions, Y)
			logging.info(f'Epoch: {i}, {predictions}, {Y}, {accuracy}, {end - start}')

def make_predictions(X):
	Z, A = forward(X)
	numlayers = len(A)
	predictions = get_predictions(A[numlayers-1])
	return predictions

def train():
	initModel()
	#fixModel()   # for debugging
	X,Y,m = prepTrainingData()
	gradient_descent(X, Y, config['alpha'], config['epochs'], m)
	writeModel()

