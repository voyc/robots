'''
nn.py - library of neural net functions
see samsonzhang.py

'''

import numpy as np

def initModel(numinputs, widths, activates, nonmaxima):
	W = []
	b = []
	prev = numinputs
	for w in widths:
		W.append(np.random.rand(w, prev) - 0.5)
		b.append(np.random.rand(w, 1) - 0.5)
		prev = w
	return [W, b, activates, nonmaxima]

def activation(code, value):
	if code == 0:
		activated = ReLU(value)
	elif code == 1:
		activated = sigmoid(value)
	elif code == 2:
		activated = softmax(value)
	return activated

def forward(model, X):
	# multi-layer version of forward_prop
	[W, b, act, nonmax] = model
	numlayers = len(W)
	Z = [0] * numlayers 
	Y = copy.deepcopy(X)
	for n in range(0, numlayers):
		Z[n] = W[n].dot(Y) + b[n]  # wx + b
		Y = activation(activates[n], Z[n]) 
	return Y

def init_params():
	W1 = np.random.rand(10, 784) - 0.5
	b1 = np.random.rand(10, 1) - 0.5
	W2 = np.random.rand(10, 10) - 0.5
	b2 = np.random.rand(10, 1) - 0.5
	return W1, b1, W2, b2

def ReLU(Z):
	# rectify linear unit
	return np.maximum(Z, 0)

def softmax(Z):
	# turn an array of numbers into a probability distribution
	A = np.exp(Z) / sum(np.exp(Z))
	return A
	
def forward_prop(W1, b1, W2, b2, X):
	Z1 = W1.dot(X) + b1  # ax+b for each X
	A1 = ReLU(Z1)	     # activation, minimum 0	
	Z2 = W2.dot(A1) + b2 # feed output of layer 1 into layer 2
	A2 = softmax(Z2)     # convert to probability distribution
	return Z1, A1, Z2, A2

def ReLU_deriv(Z):
	return Z > 0

def one_hot(Y):
	one_hot_Y = np.zeros((Y.size, Y.max() + 1))
	one_hot_Y[np.arange(Y.size), Y] = 1
	one_hot_Y = one_hot_Y.T
	return one_hot_Y

def backward_prop(Z1, A1, Z2, A2, W1, W2, X, Y, m):
	one_hot_Y = one_hot(Y)
	dZ2 = A2 - one_hot_Y   # subtract one_hot_Y from A2
	dW2 = 1 / m * dZ2.dot(A1.T)
	db2 = 1 / m * np.sum(dZ2)
	dZ1 = W2.T.dot(dZ2) * ReLU_deriv(Z1)
	dW1 = 1 / m * dZ1.dot(X.T)
	db1 = 1 / m * np.sum(dZ1)
	return dW1, db1, dW2, db2

def update_params(W1, b1, W2, b2, dW1, db1, dW2, db2, alpha):
	W1 = W1 - alpha * dW1
	b1 = b1 - alpha * db1	
	W2 = W2 - alpha * dW2  
	wr2 = b2 - alpha * db2	
	return W1, b1, W2, b2

def get_predictions(A2):
	return np.argmax(A2, 0)

def get_accuracy(predictions, Y):
	return np.sum(predictions == Y) / Y.size

def gradient_descent(X, Y, alpha, iterations, m):
	W1, b1, W2, b2 = init_params()
	for i in range(iterations):
		Z1, A1, Z2, A2 = forward_prop(W1, b1, W2, b2, X)
		dW1, db1, dW2, db2 = backward_prop(Z1, A1, Z2, A2, W1, W2, X, Y, m)
		W1, b1, W2, b2 = update_params(W1, b1, W2, b2, dW1, db1, dW2, db2, alpha)
		if i % 10 == 0:
			predictions = get_predictions(A2)
			accuracy = get_accuracy(predictions, Y)
			print(f'Iteration: {i}, {predictions}, {Y}, {accuracy}')
	return W1, b1, W2, b2

def make_predictions(X, W1, b1, W2, b2):
	_, _, _, A2 = forward_prop(W1, b1, W2, b2, X)
	predictions = get_predictions(A2)
	return predictions
