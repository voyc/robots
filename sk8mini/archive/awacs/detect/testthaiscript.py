'''
testthaiscript.py - work with thai script similar to mnist 

Original source of mnist data
	http://yann.lecun.com/exdb/mnist/

Secondary source of mnist data on kaggle provided by Samson Zhang
	https://www.kaggle.com/code/johnhagstrand/notebookc9090743f5/input?select=train.csv

for training, some nn systems package a large number of images in one array
	opencv proviles the dnn.blobFromImages([images]) to stack images together
	the mnist format is similar

warning: cv2 and numpy use opposite dimension order 
	see https://curriculum.voyc.com/doku.php?id=neural_network#python_packages_for_ai
'''
import cv2 as cv
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import samsonzhang as sz

# class names
gnames = 'ko_kai', 'kho_khai', 'ngo_ngu', 'yo_yak', 'cho_chan', 'pho_phan', 'tho_than', 'tho_thang', 'wo_waen', 'kho_khwai',

# image made in GIMP, 6 cols x 10 rows, 28x28 pixels 
gbase = '/home/john/media/webapps/sk8mini/awacs/photos/thaiscript/'
ginputfname = 'thaiscript_6x10.png'
ggridsize = 28
gtileext = 'png'

gfnamePixel = 'pixel.csv'  # 1 row per image, int 0-255, label in the first column
gfnameNames = 'names.txt'  # 1 column list of class names, can be indexed by label
gfnameConfig = 'config.cfg'
gfnameModel = 'model.model'

# open a grid file, slice it, reformat as array of pixels, write as csv
def prepData(base, inputfname, outputfname, gridsize):
	im = cv.imread(base+inputfname)
	im = cv.cvtColor(im, cv.COLOR_BGR2GRAY)
	im = (255 - im)  # invert b/w
	height, width = im.shape
	
	# cut tiles out of grid file and flatten tile to row
	tiles = []
	pixels =  []
	for nrow in range(0, int(height/gridsize)):   # 10 rows
		top = nrow * gridsize
		bottom = (nrow+1) * gridsize
		for ncol in range(0, int(width/gridsize)):   # 6 columns
			left = ncol * gridsize
			right = (ncol+1) * gridsize
			tile = im[top:bottom, left:right]
			tiles.append(tile)

			pixel = np.concatenate(tile)  # flatten tile to row
			pixel = np.insert(pixel, 0, nrow)  # insert label in column 1
			pixels.append(pixel)
	pixels = np.array(pixels)

	# write to csv
	df = pd.DataFrame(pixels)
	df.to_csv(base+outputfname, index=False, header=False) 
	return tiles, pixels

def test_prediction(index, X_train, Y_train, W1, b1, W2, b2):
	current_image = X_train[:, index, None]
	prediction = sz.make_predictions(X_train[:, index, None], W1, b1, W2, b2)
	label = Y_train[index]
	print("Prediction: ", prediction)
	print("Label: ", label)
	
	current_image = current_image.reshape((28, 28)) * 255
	plt.gray()
	plt.imshow(current_image, interpolation='nearest')
	plt.show()


def main():
	#prepData(gbase, ginputfname, gfnamePixel, ggridsize)

	df = pd.read_csv(gbase+gfnamePixel, header=None)
	data = df.to_numpy()
	m, n = data.shape
	print(f'read gfnamePixel, shape: { data.shape}')

	# split into training and validation sets, and normalize to 0:1
	np.random.shuffle(data) # shuffle 
	
	data_validate = data[0:10].T	# first 10 rows, transposed to columns
	Y_validate = data_validate[0]	# first column is labels
	X_validate = data_validate[1:n] # remaining columns are pixels
	X_validate = X_validate / 255.	# normalize to 0:1
	
	data_train = data[10:m].T
	Y_train = data_train[0]		# the ground truth Y
	X_train = data_train[1:n]
	X_train = X_train / 255.	# for given image X


	# train
	W1, b1, W2, b2 = sz.gradient_descent(X_train, Y_train, 0.10, 25000, m)

	# predict
	test_prediction(0, X_validate, Y_validate, W1, b1, W2, b2)
	test_prediction(1, X_validate, Y_validate, W1, b1, W2, b2)
	test_prediction(2, X_validate, Y_validate, W1, b1, W2, b2)
	test_prediction(3, X_validate, Y_validate, W1, b1, W2, b2)

if __name__ == '__main__':
	main()

