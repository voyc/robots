'''
testsamsonzhang.py

SAMSON ZHANG:  Simple MNIST NN from scratch (numpy, no TF/Keras)

https://www.kaggle.com/code/wwsalmon/simple-mnist-nn-from-scratch-numpy-no-tf-keras
https://youtu.be/w8yWXqWQYmU

'''

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import samsonzhang as sz

# input data into np array
#data = pd.read_csv('/kaggle/input/digit-recognizer/train.csv')
data = pd.read_csv('photos/samson/train.csv')
data = np.array(data)
m, n = data.shape
print(data.shape)

np.random.shuffle(data) # shuffle 

# split into dev and training sets, where dev means validation, and normalize to 0:1
data_dev = data[0:1000].T
Y_dev = data_dev[0]
X_dev = data_dev[1:n]
X_dev = X_dev / 255.

data_train = data[1000:m].T
Y_train = data_train[0]
X_train = data_train[1:n]
X_train = X_train / 255.
_,m_train = X_train.shape

def test_prediction(index, W1, b1, W2, b2):
	current_image = X_dev[:, index, None]
	prediction = sz.make_predictions(X_dev[:, index, None], W1, b1, W2, b2)
	label = Y_dev[index]
	print("Prediction: ", prediction)
	print("Label: ", label)
	
	current_image = current_image.reshape((28, 28)) * 255
	plt.gray()
	plt.imshow(current_image, interpolation='nearest')
	plt.show()

# train
W1, b1, W2, b2 = sz.gradient_descent(X_train, Y_train, 0.10, 500, m)

# begin insert code
import json
model = {
	'W1': W1.tolist(),
	'b1': b1.tolist(),
	'W2': W2.tolist(),
	'b2': b2.tolist()
}
with open('photos/samson/samsonmodel.json', 'w') as f:
	f.write(json.dumps(model))
# end insert code

# predict
test_prediction(0, W1, b1, W2, b2)
test_prediction(1, W1, b1, W2, b2)
test_prediction(2, W1, b1, W2, b2)
test_prediction(3, W1, b1, W2, b2)


