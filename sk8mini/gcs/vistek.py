'''
vistek.py - visual cortex: detect cones in one frame
'''

import cv2
import numpy as np
import math
import logger

def setup():
	return True

def getCoordinates(frame):
	cones = getCones(frame)
	getSk8(frame)
	return cones

def getCones(frame, model):
	dim, weight, bias, minp = model

	fw,fh,fd = frame.shape
	sz = max(dim)

	# get saturation channel
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	_,sc,_ = cv2.split(hsv)

	# calc threshold via linear eqation ax+b, weight * x + bias
	x = np.mean(sc)
	threshold = weight * x + bias

	# create mask from threshold
	_, mask = cv2.threshold(sc, threshold,  255, cv2.THRESH_BINARY)

	# create labels from mask contours
	cls = 1
	p = 0
	labels = []
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	for cnt in cnts:
		(x,y), (w,h), θ = cv2.minAreaRect(cnt) 

		# qualify by size, calc probability
		rmse = calcRMSE((w,h), dim)
		p = max(0, sz - rmse) / sz
		if p < minp:
			continue

		# normalize label values
		x = x / fw
		y = y / fh
		w = w / fw
		h = h / fh
		θ = θ / 360
		labels.append([cls, x,y, w,h, θ, p])
	return labels

# mean squared error
def calcMSE(predicted, actual):
	actual = np.array(actual) 
	predicted = np.array(predicted) 
	differences = np.subtract(actual, predicted)
	squared_differences = np.square(differences)
	mean = squared_differences.mean()
	return mean

# root mean squared error
def calcRMSE(predicted, actual):
	mse = calcMSE(predicted, actual)
	rmse = math.sqrt(mse)
	return rmse

def coneLossFunction(predicted, actual):
	return error

def getSk8(frame):
	pass
