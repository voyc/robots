'''
testimage.py - test image processing techniques for object detection
originally taken from tello murtaza

image - the image is a numpy array.

shape - a grayscale image has 2 dimensions.  BGR and HSV images have 3 dimensions.

image processing - There are multiple ways to manipulate the numpy array:
  - a python for-loop (slow)
  - a numpy vector math method (fast)
  - methods of an image processing package, like:
    . opencv: computer vision
    . matplotlib: similar to MatLab
    . scikit-learn, aka sklearn: machine learning
    . scipy: optimization, linear regression, image processing, etc.

computer vision - image processing with a purpose: to approximate human understanding of an image.

object detection - find and classify objects in an image.  Two ways:
  . computer vision, algorithmic
  . neural net, non-algorithmic AI (not discussed here)

computer vision algorithm for object detection
  input: image
  output: list of objects

object - a polygon. normally represented by a bounding box

mask - white on black. The stuff we want is white; throwaway background is black.

contour - a polygon.  A numpy array of x,y coordinates.

edge detection - find lines of high contrast between light and dark areas of an image.


Methods of edge detection:
	findContours() - returns a list of polygons
	Canny() - returns a mask of white lines on black background


Ways to create the mask.

- Select by HSV.color.  Use HSV image and inRange(low, high).
	a. For black, look for low values of Value.
	b. For white, look for high values of Sat.
	c. For other colors, start with a Hue range, then tweak by Value and Sat.

- Select by Grayscale.  Alternative for black and white.  Use inRange() or threshold().

- Select by Canny edge.  Use Grayscale image.  Canny(lo, hi).
	a. Resulting mask is lines.
	b. Use dilate() to thicken and connect the lines into objects.

- drawContours() onto a background.


object detection algorithm using computer vision
	step 1.  mask
	step 2.  list of polygons
	step 3.  list of bounding boxes 
'''

import numpy as np
import cv2
import os
import math

import draw

def showImage(*args):
	print(len(args))
	a = []
	for img in args:
		if len(img.shape) < 3:
			newimg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
			a.append(newimg)
		else:
			a.append(img)
	print(len(a))
	for img in a:
		print(img.shape)
	imgOut = np.hstack(a)
	cv2.imshow('show image', imgOut)
	key = cv2.waitKey(0)
	cv2.destroyAllWindows()

def drawLine(img, ctr, angle, length=100):
	x = ctr[0]
	y = ctr[1]
	θ = angle * 3.14 / 180.0
	x2 = int(x + length * math.cos(θ))
	y2 = int(y + length * math.sin(θ))
	x3 = int(x - length * math.cos(θ))
	y3 = int(y - length * math.sin(θ))
	cv2.line(img, (x2,y2), (x3,y3), (0,0,255), 1)

def drawVehicle(img, vehicle):
	box = vehicle[0]	
	ctr = vehicle[1]	
	angle = vehicle[2]	
	cv2.drawContours(imgBgr, [box], 0, (0,0,255),1)
	drawLine(imgBgr, ctr, angle, 50)

def averageBrightness(image):
	imgHsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
	t = imgHsv[:,:,2]   # take the V channel, "value", brightness
	mean = np.mean(t)
	return mean

# read image
model = 'photos/training/day_model.json'
fname = 'photos/20231216-092941/00134.jpg'   # donut 143
fname = 'photos/20231216-092941/00103.jpg'   # donut 173
imgBgr = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
brightness = averageBrightness(imgBgr)

imgHsv = cv2.cvtColor(imgBgr, cv2.COLOR_BGR2HSV)
imgGray = cv2.cvtColor(imgBgr, cv2.COLOR_BGR2GRAY)

# mask based on hsv ranges
lower = np.array([23, 114,  57])
upper = np.array([37, 225, 205])
imgMaskYellow = cv2.inRange(imgHsv,lower,upper)

# invert mask
imgInvertedMask = cv2.bitwise_not(imgMaskYellow)

# mask based on gray values
imgMaskBlack = cv2.inRange(imgGray, 10, 50)  # looking for black
imgMaskWhite = cv2.inRange(imgGray, 100, 250)  # looking for white


# make square mask around vehicle
sz = np.array([ 50, 50])
ctr = np.array([323,145])
lt = ctr - sz
rb = ctr + sz
l,t = lt
r,b = rb
color = (255,255,255)
thickness = -1

imgCrop = imgBgr[t:b, l:r]

imgVehicleMask = np.zeros(sz, np.uint8)
imgVehicleMask = cv2.rectangle(imgVehicleMask, lt, rb, color, thickness) 

# remove background
#imgCropInv = cv2.bitwise_not(imgCrop)
#imgMasked = cv2.bitwise_and(imgBgr,imgBgr, mask=imgVehicleMask)
draw.showImage(imgVehicleMask)

# canny edge detection
imgCanny = cv2.Canny(imgCrop, 50, 70)

kernel = np.ones((5, 5))
imgClosed = cv2.morphologyEx(imgCanny, cv2.MORPH_CLOSE, kernel)

showImage(imgCrop, imgCanny, imgClosed)

# dilate
imgMaskVehicle = cv2.dilate(imgCanny, kernel, iterations=3)

#showImage(imgMaskVehicle)
showImage(imgCanny)

contours, _ = cv2.findContours(imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f'num contours: {len(contours)}')

polygon = []
counter = 0
for cnt in contours:
	counter += 1
	print(f'{counter} len cnt: {len(cnt)}')
	for c in cnt:
		print(c[0])
		polygon.append(c[0])

	#polygon += cnt

	rect = cv2.minAreaRect(cnt)
	box = cv2.boxPoints(rect)
	box = np.intp(box)

	#qualify by size
	w = rect[1][0]
	h = rect[1][1]
	if w<25 or h<25:
		continue

	#print(fname)
	#print(rect)
	#print(cv2.boundingRect(cnt))
	#print(cv2.minEnclosingCircle(cnt))
    

	ctr = rect[0]
	ctr = np.intp(ctr)
	angle = rect[2]
	#print(f'ctr:{ctr}, angle:{angle}')

	vehicle = (box, ctr, angle)
	print(ctr)
	drawVehicle(imgBgr, vehicle)
showImage(imgBgr)

poly = [[83,38],[82,56],[74,71],[71,74],[30,74],[28,73],[15,55],[15,37],[16,36],[18,35],[34,28],[59,27],[67,27],[81,35]]
poly = np.array(poly)
print(poly)

polygon = np.array(polygon)
print(polygon)

hull = cv2.convexHull(polygon)
print(hull)

mask = draw.createMask((100,100))
#mask = cv2.polylines(mask, polygon, True, (255,255,255), 1)
#mask = cv2.polylines(mask, hull, True, (255,255,255), 1)
cv2.drawContours(mask, [hull], -1, color, cv2.FILLED)
showImage(mask)

'''
		
	# step 2. apply the mask to the original.  no settings.
	imgMasked = cv2.bitwise_and(img,img, mask=imgMask)

	# step 3. apply Gaussian Blur.  settings fixed.
	imgBlur = cv2.GaussianBlur(imgMasked, (gaus1, gaus2), gausblur)

	# step 4. convert to grayscale.  no settings.
	imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_BGR2GRAY)

	# step 5. canny edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
	imgCanny = cv2.Canny(imgGray, settings['canny_lo'], settings['canny_hi'])

	# step 6. dilate, thicken, the edge lines.  settings fixed.
	kernel = np.ones((dilate1, dilate2))
	imgDilate = cv2.dilate(imgCanny, kernel, iterations=dilateiter)
	imgEdged = imgDilate.copy()

'''
