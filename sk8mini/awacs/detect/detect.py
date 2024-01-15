'''
detect.py - object detection library, using image processing
'''

import numpy as np
import cv2
import os

import label as labl

def getFrameList(path):
	flist = []
	for filename in os.listdir(path):
		fnum, ext = os.path.splitext(filename)
		if ext == '.jpg':
			flist.append(fnum)
	return sorted(flist)

def averageBrightness(image):
	imgHsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
	t = imgHsv[:,:,2]   # take the V channel, "value", brightness
	mean = np.mean(t)
	return mean

def detectObjectsCls(img,modcls):
	def inRange( a, lower, upper):  # comparing np arrays
		return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

	#modcls = model[cls]
	cls = int(modcls['cls'])
	sp = modcls['values']

	if modcls['algo']  == 0:  # hsv color values
		[cn,cx,sn,sx,vn,vx,wn,wx,hn,hx] = modcls['values']
		#lower = np.array([sp[0], sp[2], sp[4]])
		#upper = np.array([sp[1], sp[3], sp[5]])
		lower = np.array([cn,sn,vn])
		upper = np.array([cx,sx,vx])
		imgMask = cv2.inRange(img,lower,upper)

	else:
		[gray,wn,wx,hn,hx] = modcls['values']
		if modcls['algo'] == 1:   # grayscale white
			threshtype = cv2.THRESH_BINARY
		elif modcls['algo'] == 2:   # grayscale black
			threshtype = cv2.THRESH_BINARY_INV
		imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		ret, imgMask = cv2.threshold(imgGray, gray, 255, threshtype)
		
	dilate1 = 5
	dilate2 = 5
	dilateiter = 1
	kernel = np.ones((dilate1, dilate2))
	imgMask = cv2.dilate(imgMask, kernel, iterations=dilateiter)

	contours, _ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

	imgMask = cv2.cvtColor(imgMask, cv2.COLOR_GRAY2BGR)
	#imgMask = cv2.drawContours(imgMask, contours, -1, (128,128,255), 3)

	#qualify by size
	labels = []
	for cnt in contours:
		if modcls['rotate']:
			rect = cv2.minAreaRect(cnt) 
			label = labl.labelFromRect(cls,rect)
		else:
			bbox = cv2.boundingRect(cnt)
			label = labl.labelFromBbox(cls,bbox)

		size = labl.sizeFromLabel(label)

		#lensp = len(sp)
		#wn = lensp - 4
		#wx = lensp - 3
		#hn = lensp - 2
		#hx = lensp - 1
		#lowerSize = np.array([sp[wn], sp[hn]])
		#upperSize = np.array([sp[wx], sp[hx]])
		lowerSize = np.array([wn,hn])
		upperSize = np.array([wx,hx])

		if inRange(size, lowerSize, upperSize):
			labels.append(label)

	#print(f'contours found: {len(contours)}, qualified by size: {len(labels)}')
	return labels, imgMask

def detectObjects(img,model):
	labels = []
	for modcls in model:
		lbls,_ = detectObjectsCls(img, modcls)
		labels += lbls
	labels = crossClassAdjustments(labels)
	return labels


def crossClassAdjustments(labels):
	#led 
	#sk8

	return labels
