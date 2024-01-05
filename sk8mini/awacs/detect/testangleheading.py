'''
testangleheading.py - 

returned from minAreaRect():
(cx,cy), (w,h), a

returned from boxPoints():
four points
the first point is the left-top (lowest x, with lowest y as tie-breaker)
remaining points proceed clockwise
1st line segment is considered h
2nd line segment is considered w

when rect is upright, h > w
when rect is supine,  w > h
when rect is square, the 1st line segment is the top, not the side
	therefore, a is never 0, it goes to 90
	(in a similar way, hdg is never 360, it goes to 0)

'''

import numpy as np
import cv2
import math

def linelen(pt0, pt3):
	a = pt3[1] - pt0[1]
	b = pt3[0] - pt0[0]
	hyp = math.sqrt(a**2 + b**2)
	return hyp

def fudgeRect(rect):
	# input a is 1 to 90, h and w are interchangeable
	(cx,cy),(w,h),a = rect

	# output a is 1 to 180, h>w always
	if w > h:
		w,h = (h,w)
		a += 90

	cx = round(cx)
	cy = round(cy)
	w = round(w)
	h = round(h)
	a = round(a)

	return (cx,cy),(w,h),a

def reverseHeading(hdg):
	rhdg = hdg + 180
	if rhdg >= 360:
		rhdg -= 360
	return rhdg

def getHeadingFromAngle(angle):
	hdg = angle
	rhdg = reverseHeading(hdg)
	return hdg,rhdg

def testrrect(hdg):
	fname = f'/home/john/media/webapps/sk8mini/awacs/photos/training/test_angle_heading/rect_{hdg}.jpg'
	img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
	imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	ret, thresh = cv2.threshold(imgray, 127, 255, 0)
	contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnt = contours[0]

	# original rect returned from minAreaRect()
	rect = cv2.minAreaRect(cnt)
	(cx,cy),(w,h),a = rect
	#print(hdg, a, w, h)

	# fudged rrect
	rrect = fudgeRect(rect)
	(cx,cy),(w,h),a = rrect
	chdg = getHeadingFromAngle(a)
	print(hdg, a, w, h, chdg)

	# optional, examine points and lines in the rect
	box = cv2.boxPoints(rect)
	box = np.intp(box)
	ln01= linelen(box[0], box[1])
	ln03= linelen(box[0], box[3])
	return rect

testrrect('10')  
testrrect('45')  
testrrect('80')  
testrrect('90')  
testrrect('100') 
testrrect('135') 
testrrect('170') 
testrrect('180')   


quit()





# read image
fname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test_angle_heading/rect_0.jpg'
img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
print(img.shape)

imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
ret, thresh = cv2.threshold(imgray, 127, 255, 0)
print(thresh.shape)

contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(len(contours))

cnt = contours[0]
print(cnt)

rect = cv2.minAreaRect(cnt)
print(rect)


#	box = cv2.boxPoints(rect)
#	box = np.intp(box)
