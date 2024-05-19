'''
testnn.py - test the nn library
see testsamsonzhang.py

python3 --task classify --iimage 8jdig0.png --display
python3 -Wi::DeprecationWarning testnn.py --task train
'''

import numpy as np
from matplotlib import pyplot as plt
import cv2
import argparse
import logging
import os
import glob
import nn

def getArguments():
	parser = argparse.ArgumentParser()
	parser.add_argument('-t'  ,'--task'      ,default='train'      ,choices=['classify','train','sim'] ,help='task: train, classify, sim'	)
	parser.add_argument('-cf' ,'--config'    ,default='photos/jdig/single/config.yaml'           ,help='filename of config file'		)
	parser.add_argument('-im' ,'--image'     ,default='0jdig0.png'                               ,help='input image for classification'	)



	parser.add_argument('-v'  ,'--verbose'   ,default=False        ,action='store_true'          ,help='display additional logging'		)
	parser.add_argument('-q'  ,'--quiet'     ,default=False        ,action='store_true'          ,help='suppresses all output'		)
	parser.add_argument('-d'  ,'--display'   ,default=False        ,action='store_true'          ,help='display the input image'		)
	args = parser.parse_args()	# returns Namespace object, use dot-notation
	return args

def setupLogging(verbose,quiet):
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)

def main():
	args = getArguments()

	setupLogging(args.verbose, args.quiet)
	logging.debug(args)

	nn.readConfig(args.config)
	logging.debug(nn.config)

	if args.task == 'train':
		nn.train()

	elif args.task == 'classify':
		nn.readModel()
		X,y = preprocess(nn.config['folder'] + args.image)
		prediction = classify(X, y)
		if args.display:
			current_image = X.reshape((28,28)) * 255
			plt.gray()
			plt.imshow(current_image, interpolation='nearest')
			plt.show()

	elif args.task == 'sim':
		sim()
		
def sim():   # camera simulation
	nn.readModel()
	pattern = nn.config['pattern']
	flist = glob.glob(pattern)
	flist = sorted(flist)
	ndx = -1
	total = 0
	correct = 0

	def getFname():
		nonlocal ndx
		ndx += 1
		if ndx >= len(flist):
			return None
		return flist[ndx]

	def score(prediction, y):
		nonlocal total, correct
		total += 1
		if prediction - y == 0:
			correct += 1

	while True:
		fname = getFname()
		if not fname: break
		X,y = preprocess(fname)
		prediction = classify(X,y)
		score(prediction, y)

	prob = correct/total if total > 0 else 0
	logging.info(f'correct:{correct}, total:{total}, prob:{prob}')

def classify(X,y):
	prediction = nn.make_predictions(X)
	logging.info(f'prediction: {prediction[0]},  truth: {y}')
	return prediction[0]
	
def preprocess(fname):
	y = os.path.basename(fname)[0]
	y = int(y)     # first char of the filename is the cls index
	img = cv2.imread(fname)
	img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	X = img.reshape((784,1))
	X = (255 - X)  # invert b/w
	X = X / 255    # normalize
	return X,y


if __name__ == '__main__':
	main()
