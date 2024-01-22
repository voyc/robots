'''
label.py - label management library

A label is a two-dimensional list of integers, 
one row for each detected object in an image.

A label object is stored in a .csv file.
example filenames:
00001.jpg - the image
00001_label.csv - the label file
00001_truth.csv - a perfected label file, "ground truth", used for training

Three use cases:
	1. training: compare computed label to truth
	2. serving: realtime data broadcast and used for navigation

The typical label file in AI is a bbox, plus optional keypoints.

sk8 Format
	the first column is the classifier
	the next five columns represent the rotated rectangle

this list is assumed to have been sorted, ala sorted(label)

''' 

import csv
import math

# global constants
# index the 7 columns of a label list
cls = 0	 # clsid 1:cone, 2:led, 3:sk8
cx  = 1	 # centerpoint
cy  = 2
w   = 3   # size
h   = 4
hdg = 5   # heading
scr = 6   # score, error
m   = 7   # match, used temporarily during scoring

# cls,cx,cy,w,h,hdg,scr = label

def read(fname):
	label = []
	with open(fname, 'r') as f:
		reader = csv.reader(f)
		for srow in reader:
			irow = []
			n = 0
			for cell in srow:
				if n == scr:
					irow.append(float(cell))
				else:
					irow.append(int(cell))
				n += 1
			label.append(irow)
		return label

def write(label, fname):
	with open(fname, 'w') as f:
		wr = csv.writer(f)
		wr.writerows(label)

# output string formats
def format(labels, format='display'):
	s = ''
	if format == 'realtime':
		ctrs = []
		for label in labels:
			cls,cx,cy,w,h,hdg,scr = label
			if cls == 3:
				ctrs.insert(0, (cx,cy,hdg))
			else:
				ctrs.append((cx,cy))
		s = str(ctrs)
	elif format == 'display':
		for label in labels:
			s += str(label)+'\n'
	return s

#------------------- data structures ------------------#
'''	
data structures:
	label - [cls, cx,cy,w,h,hdg, scr] - sk8mini format
	rect  - ((cx,cy), (wr,hr), angle) - rotated rect returned from cv2,minAreaRect(contour)
	bbox  - left,top,w,h - bounding box returned from cv2.boundingRect(contour)

also: 
	labels - a list of of label objects

notes on rotated rect
	when rect is upright, h > w
	when rect is supine,  w > h
	when rect is square, the 1st line segment is the top, not the side
		therefore, a is never 0, it goes to 90
		(in a similar way, hdg is never 360, it goes to 0)

To better understand the rect, look at the four points returned from cv2.boxPoints(rect)
	the first point is the left-top (lowest x, with lowest y as tie-breaker)
	remaining points proceed clockwise
	1st line segment is considered h
	2nd line segment is considered w
'''

def labelFromBbox(cls,bbox):
	# 1. calc centerpoint (cx,cy) from (left,top)
	# 2. set hdg to 0
	
	left,top,w,h = bbox
	cx = left + (w/2)
	cy = top + (h/2)

	cls = int(cls)
	cx = round(cx)
	cy = round(cy)
	w = round(w)
	h = round(h)
	hdg = 0
	scr = 0
	return [cls,cx,cy,w,h,hdg,scr]

def labelFromRect(cls, rect, which=False, score=0):
	# 1. if necessary, rotate 90° so that h > w always
	# 2. calc heading hdg from angle 

	(cx,cy),(w,h),a = rect
	if w > h:
		w,h = (h,w)
		a += 90

	hdg = headingFromAngle(a, which)

	cls = int(cls)
	cx = round(cx)
	cy = round(cy)
	w = round(w)
	h = round(h)
	hdg = round(hdg)
	scr = score
	return [cls,cx,cy,w,h,hdg,scr]

def sizeFromLabel(label):
	_,_,_,w,h,_,_ = label
	size = (w,h)
	return size

# length of hypotenuse via pythagorean theorem
def linelen(ptA, ptB):
	a = ptB[1] - ptA[1]
	b = ptB[0] - ptA[0]
	hyp = math.sqrt(a**2 + b**2)
	return hyp

#def rect2rrect(rect):
#def fudgeRect(rect):
#	# input a is 1 to 90, h and w are interchangeable
#	(cx,cy),(w,h),a = rect
#
#	# output a is 1 to 180, h>w always
#	if w > h:
#		w,h = (h,w)
#		a += 90
#
#	cx = round(cx)
#	cy = round(cy)
#	w = round(w)
#	h = round(h)
#	a = round(a)
#
#	return (cx,cy),(w,h),a


#-------------------------- angle vs heading -------------------#
'''
original angle returned from cv2.minAreaRect() is 1 to 90
fudged angle is from 1 to 180
heading is from 0 to 259

angle implies two alternate headings: one to the east, one to the west
additional data is required to narrow the choice to one heading.
'''
def reverseHeading(hdg):
	rhdg = hdg + 180
	if rhdg >= 360:
		rhdg -= 360
	return rhdg

def headingFromAngle(angle, which='east'):
	hdg = angle
	rhdg = reverseHeading(hdg)
	if which == 'east':
		return hdg
	elif which == 'west':
		return rhdg
	elif which == 'both':
		return hdg,rhdg
	return hdg

