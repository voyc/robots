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

def showImage(img):
	cv2.imshow('show image', img)
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

# read image
fname = '/home/john/media/webapps/sk8mini/awacs/photos/training/00095.jpg'
#fname = '/home/john/media/webapps/sk8mini/awacs/photos/training/00002.jpg'
#fname = '/home/john/media/webapps/sk8mini/awacs/photos/training/00001.jpg'
imgBgr = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
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

#showImage(imgMaskYellow)
#showImage(imgMaskBlack)
#showImage(imgMaskWhite)

contours, _ = cv2.findContours(imgMaskYellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
#print(len(contours))
#img = cv2.drawContours(imgBgr, contours, -1, (0,0,255),1)
#showImage(img)

imgCanny = cv2.Canny(imgGray, 50, 70)
#showImage(imgGray)
#showImage(imgCanny)
#showImage(imgMaskYellow)

#paramloop
#	pairloop
params = [
	(0,17),
	(117,195),
	(47,128)
]

#       x  y   a
#00001 50 30  54
#00002 45 22   9   # horizontal, xdim=w, ydim=h  when x-axis is horizontal
#00095 50 30  54   # vertical,   xdim=h, ydim=w  when x-axis is vertical  ?
#(57.881370544433594, 37.80196762084961)
# 00001: (44.904972076416016, 66.58959197998047), 10.619654655456543)

#file      xdim  ydim  angle    w    h     r
#00001.jpg   44    66     10   52   65    33    x-axis crosswise, 10dgr ccw from horizontal
#00002.jpg   29    65     84   67   33    33    x-axis crosswise, 86dgr ccw from horizontal
#00095.jpg   57    37     49   58   57    30    x-axis lengthwise, 49dgr ccw from horizontal
'''
xdim = rect[1][0]
ydim = rect[1][1]

if xdim < ydim:
	beam = xdim
	leng = ydim
	a = angle + 90
else:
	leng = xdim
	beam = ydim
	a = angle 

heading = a - 90
if heading < 0:
	heading = 360 - heading

qualify by size
'''

# find vehicle by deck color
lower = np.array([ 0, 117,  47])  #00002, 00095
upper = np.array([17, 195, 128])
lower = np.array([ 0, 127,   0])  #00001
upper = np.array([63, 255, 128])
imgMaskVehicle = cv2.inRange(imgHsv,lower,upper)
showImage(imgMaskVehicle)

contours, _ = cv2.findContours(imgMaskVehicle, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#print(len(contours))


for cnt in contours:
	rect = cv2.minAreaRect(cnt)
	box = cv2.boxPoints(rect)
	box = np.intp(box)

	#qualify by size
	w = rect[1][0]
	h = rect[1][1]
	if w<25 or h<25:
		continue

	print(fname)
	print(rect)
	print(cv2.boundingRect(cnt))
	print(cv2.minEnclosingCircle(cnt))
    

	ctr = rect[0]
	ctr = np.intp(ctr)
	angle = rect[2]
	#print(f'ctr:{ctr}, angle:{angle}')

	#cv2.drawContours(imgBgr, [box], 0, (0,0,255),1)
	#drawLine(imgBgr, ctr, angle, 50)

	vehicle = (box, ctr, angle)
	drawVehicle(imgBgr, vehicle)


showImage(imgBgr)


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

