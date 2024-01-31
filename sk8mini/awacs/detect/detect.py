'''
detect.py - object detection library, using image processing
'''

import numpy as np
import cv2
import os

import label as lbl
import score as scr

def inRange( a, lower, upper):
	return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

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

#----- begin new --------------------------------
def detectColor(modcls, frame):
	#"values": [0, 69, 108, 156, 77, 148, 14, 40, 15, 40],  #night
        #"values": [ 27, 76, 119, 255, 101, 196, 11, 27, 11, 27], #day
	[cn,cx,sn,sx,vn,vx,wn,wx,hn,hx] = modcls['values']
	lower = np.array([cn,sn,vn])
	upper = np.array([cx,sx,vx])
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	mask = cv2.inRange(hsv,lower,upper)

	mask = preprocessMask(mask)
	labels = labelsFromMask(mask, modcls['cls'], modcls['dim'], modcls['count'])

	return labels, mask

def labelsFromMask(mask, cls, dim, maxcount):  # with size closest to expected dimensions 
	labels = []
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	armse = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		size = rect[1]
		rmse = scr.calcRMSE(dim, size)
		armse.append(rmse)
		label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
		labels.append(label)

	if len(labels) <= 0:
		return [lbl.notfound]

	# sort the labels ascending by error
	sortedlabels = sorted(labels, key=lambda a: a[lbl.scr])

	# take the n with lowest score
	if maxcount > 0:
		bestlabels = sortedlabels[0:maxcount]
	else:
		bestlabels = sortedlabels

	# convert error to probability
	maxerror = max(armse)
	for label in bestlabels:
		rmse = label[lbl.scr]
		prob = scr.calcProbability(rmse, maxerror)
		label[lbl.scr] = prob
	return bestlabels

def preprocessMask(mask):
	kernelsize = 3
	dilateiterations = 3
	kernel = np.ones((kernelsize, kernelsize))
	#mask = cv2.dilate(mask, kernel, iterations=dilateiterations)
	#mask = cv2.erode(mask, kernel, iterations=dilateiterations)
	return mask

#----- end new --------------------------------

def detectObjectsCls(img,modcls):
	def inRange( a, lower, upper):  # compare np arrays, True if a between lower and upper
		return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

	cls = int(modcls['cls'])
	sp = modcls['values']

	dilate1 = 5
	dilate2 = 5
	dilateiter = 1

	if modcls['algo']  == 0:  # hsv color values
		[cn,cx,sn,sx,vn,vx,wn,wx,hn,hx] = modcls['values']
		#lower = np.array([sp[0], sp[2], sp[4]])
		#upper = np.array([sp[1], sp[3], sp[5]])
		lower = np.array([cn,sn,vn])
		upper = np.array([cx,sx,vx])
		imgHsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
		imgMask = cv2.inRange(imgHsv,lower,upper)

	elif modcls['algo'] < 3:
		[gray,wn,wx,hn,hx] = modcls['values']
		if modcls['algo'] == 1:   # grayscale white
			threshtype = cv2.THRESH_BINARY
		elif modcls['algo'] == 2:   # grayscale black
			threshtype = cv2.THRESH_BINARY_INV
		imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		ret, imgMask = cv2.threshold(imgGray, gray, 255, threshtype)

	elif modcls['algo'] == 3:  # canny
		[vn,vx,ds,di,wn,wx,hn,hx] = modcls['values']
		imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		imgMask = cv2.Canny(imgGray, vn, vx)
		dilate1 = dilate2 = ds
		dilateiter = di
		
	kernel = np.ones((dilate1, dilate2))
	imgMask = cv2.dilate(imgMask, kernel, iterations=dilateiter)
	#imgMask = cv2.erode(imgMask, kernel, iterations=dilateiter) # not with donuts

	contours, _ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

	imgMask = cv2.cvtColor(imgMask, cv2.COLOR_GRAY2BGR)
	#imgMask = cv2.drawContours(imgMask, contours, -1, (128,128,255), 3)

	#qualify by size
	labels = []
	for cnt in contours:
		if modcls['rotate']:
			rect = cv2.minAreaRect(cnt) 
			label = lbl.labelFromRect(cls,rect)
		else:
			bbox = cv2.boundingRect(cnt)
			label = lbl.labelFromBbox(cls,bbox)

		size = lbl.sizeFromLabel(label)

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

def detectObjectsCls(img, modcls):
	return detectColor(modcls, img)

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

