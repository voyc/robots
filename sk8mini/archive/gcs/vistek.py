'''
vistek.py - visual cortex: detect cones in one frame
'''

import cv2
import numpy as np
import math
import logger

ikernel = '/home/john/media/webapps/sk8mini/awacs/photos/crop/donutfilter.jpg'
donutkernel = None

def setup():
	global donutkernel
	kernel = cv2.imread(ikernel)
	kernel = cv2.cvtColor(kernel, cv2.COLOR_BGR2GRAY)
	kernel = ((kernel / 255) - 0.5) * 2 # normalize to -1:+1
	donutkernel = kernel
	return True

def linelen(A,B):
	ax,ay = A
	bx,by = B
	a = ax - bx
	b = ay - by
	hyp = np.sqrt(a**2 + b**2)
	return hyp

def getCoordinates(frame):
	cones = getCones(frame)
	sk8 = getSk8(frame)

	ccones = []
	for co in cones:
		if linelen(co,sk8[0:2]) > 100: #40:
			ccones.append(co)

	return ccones, sk8

def getCones(frame):
	#model = {'dim':(23,23), 'weight':0.1, 'bias':119, 'minp':0.9}
	model = [(23,23), 0.1, 119, 0.9]
	dim, weight, bias, minp = model

	fw,fh,fd = frame.shape
	sz = max(dim)

	# get saturation channel
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	_,sc,_ = cv2.split(hsv)

	# calc threshold via linear eqation ax+b, weight * x + bias
	x = np.mean(sc)
	threshold = weight * x + bias
	
	threshold = 119

	# create mask from threshold
	_, mask = cv2.threshold(sc, threshold,  255, cv2.THRESH_BINARY)

	# create labels from mask contours
	cls = 1
	p = 0
	labels = []
	coords = []
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	for cnt in cnts:
		(x,y), (w,h), θ = cv2.minAreaRect(cnt) 

		## qualify by size, calc probability
		#rmse = calcRMSE((w,h), dim)
		#p = max(0, sz - rmse) / sz
		#if p < minp:
		#	continue

		# qualify by size absolute
		if w < 8 or w > 27 or h < 8 or h > 27:
			continue

		coords.append((int(x),int(y)))

		# normalize label values
		x = x / fw
		y = y / fh
		w = w / fw
		h = h / fh
		θ = θ / 360
		labels.append([cls, x,y, w,h, θ, p])
	return coords # labels

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
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = ((gray / 255) - 0.5) * 2 # normalize to -1:+1
	convolved = cv2.filter2D(gray, 1, donutkernel)
	cidx = np.argmax(convolved)
	cx = cidx % 600
	cy = int(cidx / 600)
	return [cx,cy,90]

