'''
samsonzhang.py  - library of neural net functions

SAMSON ZHANG:  Simple MNIST NN from scratch (numpy, no TF/Keras)
https://www.kaggle.com/code/wwsalmon/simple-mnist-nn-from-scratch-numpy-no-tf-keras
https://youtu.be/w8yWXqWQYmU

'''

import numpy as np
import time

def fix_params(W1,b1,W2,b2):

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

	for n in range(0,len(b1)): b1[n] = getSpray()
	for n in range(0,len(b2)): b2[n] = getSpray()

	m,n = W1.shape
	for i in range(m):
		for j in range(n):
			W1[i][j] = getSpray()
	m,n = W2.shape
	for i in range(m):
		for j in range(n):
			W2[i][j] = getSpray()

	return W1,b1,W2,b2

def init_params():
    W1 = np.random.rand(10, 784) - 0.5
    b1 = np.random.rand(10, 1) - 0.5
    W2 = np.random.rand(10, 10) - 0.5
    b2 = np.random.rand(10, 1) - 0.5
    return W1, b1, W2, b2

def ReLU(Z):
    return np.maximum(Z, 0)

def softmax(Z):
    A = np.exp(Z) / sum(np.exp(Z))
    return A
    
def forward_prop(W1, b1, W2, b2, X):
    Z1 = W1.dot(X) + b1
    A1 = ReLU(Z1)
    Z2 = W2.dot(A1) + b2
    A2 = softmax(Z2)
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
    dZ2 = A2 - one_hot_Y
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
    b2 = b2 - alpha * db2    
    return W1, b1, W2, b2

def get_predictions(A2):
    return np.argmax(A2, 0)

def get_accuracy(predictions, Y):
    return np.sum(predictions == Y) / Y.size

def gradient_descent(X, Y, alpha, iterations, m):
    global start, end
    W1, b1, W2, b2 = init_params()
    #W1, b1, W2, b2 = fix_params(W1, b1, W2, b2) # for debugging
    for i in range(iterations):
        start = time.time()
        Z1, A1, Z2, A2 = forward_prop(W1, b1, W2, b2, X)
        dW1, db1, dW2, db2 = backward_prop(Z1, A1, Z2, A2, W1, W2, X, Y, m)
        W1, b1, W2, b2 = update_params(W1, b1, W2, b2, dW1, db1, dW2, db2, alpha)
        end = time.time()
        if i % 10 == 0:
            predictions = get_predictions(A2)
            print("Iteration: ", i, predictions, Y, get_accuracy(predictions, Y), end-start)
    return W1, b1, W2, b2

def make_predictions(X, W1, b1, W2, b2):
    _, _, _, A2 = forward_prop(W1, b1, W2, b2, X)
    predictions = get_predictions(A2)
    return predictions
