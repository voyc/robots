'''
detect.py - object detection library, using image processing
'''

import numpy as np
import cv2
import label as lab

def detectObjects(img,model,cls):
	def inRange( a, lower, upper):  # comparing np arrays
		return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

	modcls = model[cls]

	if modcls['algo']  == 0:  # hsv threshholds
		sp = modcls['spec']
		lower = np.array([sp[0]['value'], sp[2]['value'], sp[4]['value']])
		upper = np.array([sp[1]['value'], sp[3]['value'], sp[5]['value']])
		imgMask = cv2.inRange(img,lower,upper)

	elif modcls['algo'] == 1:   # grayscale threshholds
		sp = modcls['spec']
		imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		mingray = int(sp[0]['value'])
		maxgray = int(sp[1]['value'])
		ret, imgMask = cv2.threshold(imgGray, mingray, maxgray, cv2.THRESH_BINARY)
		
	contours, _ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

	#qualify by size
	labels = []
	for cnt in contours:
		rect = cv2.minAreaRect(cnt) 
		label = lab.rect2label(cls,rect)
		size = (label[lab.w],label[lab.h])

		sz = modcls['size']
		lowerSize = np.array([sz[0]['value'], sz[2]['value']])
		upperSize = np.array([sz[1]['value'], sz[3]['value']])

		if inRange(size, lowerSize, upperSize):
			labels.append(label)

	print(f'contours found: {len(contours)}, qualified by size: {len(labels)}')
	return labels, imgMask

