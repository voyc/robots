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
	"format": "overlay",   # overlay, map, sbs
	"thickness_normal": 2,
	"thickness_selected": 4
}

color_stack = [
	(  0,  0,255), # red
	(255,  0,  0), # blue
	(  0,255,  0), # green
	(  0,255,255), # yellow
	(255,  0,255), # magenta
	(255,255,  0), # cyan
	(128,128,255), # pink
	(255,128,128), # ltblue
	(128,255,128), # ltgreen
	(128,255,255), # ltyellow
	(255,255,128), # ltcyan
	(255,128,255)  # ltmagenta
]

radius_stack = [ 8, 0, 5]

def drawImage(image, labels, options={}, selected=-1):
	options = default_options | options
	imgformat = options['format']

	if imgformat in ['overlay', 'sbs']:
		imgOut = imgLay = drawOverlay(image, labels, options, selected)
	if imgformat in ['map' , 'sbs']:
		imgOut = imgMap = drawMap(image, labels, options, selected)

	if imgformat == 'sbs':
		imgOut = np.hstack((image, imgLay, imgMap))
	return imgOut

def drawOverlay(image, labels, options, selected):
	imgOut = copy.deepcopy(image)
	n = 0
	for label in labels:
		cls, x, y, w, h, hdg, scr = label
		color = color_stack[cls-1]
		thickness = options['thickness_normal']
		if n == selected:
			thickness = options['thickness_selected']
		rect = ((x,y), (w,h), hdg)
		box = cv2.boxPoints(rect)
		box = np.intp(box)
		imgOut = cv2.drawContours(imgOut, [box], 0, color, thickness)

		if cls == 3:
			drawLine(imgOut, (x,y), hdg, w)
			#cv2.putText(imgOut, f'{hdg}', box[1], cv2.FONT_HERSHEY_PLAIN, 2, color)
		n += 1
	return imgOut

def drawMap(image, labels, options, selected):
	imgOut = np.full(image.shape, 255, dtype = np.uint8) 
	for label in labels:
		cls, x, y, w, h, hdg, scr = label
		color = color_stack[cls-1]
		radius = radius_stack[cls-1]
		cv2.circle(imgOut, (x,y), radius, color, -1)

		if cls == 3:
			drawLine(imgOut, (x,y), hdg, h)
	return imgOut

def titleImage(img, title):
	cv2.putText(img, title, (20,40), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0), 2)
	return img

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

