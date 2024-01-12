''' 
draw.py - library of drawing functions
'''

import cv2
import numpy as np
import copy
import math

def createImage(shape=(600,600,3), color=(255,255,255)):
	image = np.zeros(shape, np.uint8)
	image[:,:] = color
	return image

default_options = {
	"thickness_normal": 2,
	"thickness_selected": 4
}

color_stack = [
	(128,128,255), # pink
	(255,128,128), # cyan
	(128,255,128), # green
	(128,255,255), # yellow
	(255,255,128)  # cyan
]

def drawImage(image, label, options=default_options, selected=-1):
	n = 0
	imgOut = copy.deepcopy(image)
	for row in label:
		cls, x, y, w, h, hdg, scr = row
		rect = ((x,y), (w,h), hdg)
		color = color_stack[int(cls)-1]
		thickness = options['thickness_normal']
		if n == selected:
			thickness = options['thickness_selected']
		box = cv2.boxPoints(rect)
		box = np.intp(box)
		imgOut = cv2.drawContours(imgOut, [box], 0, color, thickness)

		if cls == 2:
			drawLine(imgOut, (x,y), hdg, w)
			cv2.putText(imgOut, f'{hdg}', box[1], cv2.FONT_HERSHEY_PLAIN, 2, color)
		n += 1
	return imgOut

def showImage(img):
	cv2.imshow('show image', img)
	key = cv2.waitKey(0)
	cv2.destroyAllWindows()

def drawLine(img, ctr, angle, length=100):
	x = ctr[0]
	y = ctr[1]
	θ = (angle-90) * 3.14 / 180.0   # angle in degrees to radians
	x2 = int(x + (length/2) * math.cos(θ))
	y2 = int(y + (length/2) * math.sin(θ))
	x3 = int(x - (length/2) * math.cos(θ))
	y3 = int(y - (length/2) * math.sin(θ))
	cv2.arrowedLine(img, (x3,y3), (x2,y2), (0,255,0), 2, 0, 0, 0.2)

def drawVehicle(img, vehicle):
	box = vehicle[0]	
	ctr = vehicle[1]	
	angle = vehicle[2]	
	cv2.drawContours(img, [box], 0, (0,0,255),1)
	drawLine(img, ctr, angle, 50)

