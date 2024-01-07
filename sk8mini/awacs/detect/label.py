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

# index the columns of a label list
cls = 0	# clsid 1:cone, 2:sk8
cx = 1	# centerpoint
cy = 2
w = 3   # size
h = 4
a = 5   # heading
m = 6   # match, used temporarily during scoring
e = 7   # error, used temporarily during scoring

def read(fname):
	label = []
	with open(fname, 'r') as f:
		reader = csv.reader(f)
		for srow in reader:
			irow = []
			for cell in srow:
				irow.append(int(cell))		
			label.append(irow)
		return label

def write(label, fname):
	with open(fname, 'w') as f:
		wr = csv.writer(f)
		wr.writerows(label)

# output string formats
def format(label, format='display'):
	s = ''
	if format == 'realtime':
		ctrs = []
		for row in label:
			ctrs.append([int(row[cls]), int(row[l] + (row[w])/2), int(row[t] + (row[h])/2), row[a]])
		s = str(ctrs)
	elif format == 'display':
		for row in label:
			s += str(row)+'\n'
	return s

#------------------- data structures ------------------#
'''	
data structures:
	rect - Rotated Rect, returned from minAreaRect()
	rrect - modified version of rect
	bbox - bounding box

rect

(cx,cy), (w,h), a = cv2.minAreaRect():

when rect is upright, h > w
when rect is supine,  w > h
when rect is square, the 1st line segment is the top, not the side
	therefore, a is never 0, it goes to 90
	(in a similar way, hdg is never 360, it goes to 0)

To better understand the rect, we can look at the four points returned from cv2.boxPoints(rect)
	the first point is the left-top (lowest x, with lowest y as tie-breaker)
	remaining points proceed clockwise
	1st line segment is considered h
	2nd line segment is considered w

rrect

3 adjustments are made from rect
	w and h have been normalized so w < h regardless of orientation
	a is replaced with heading
	the structure is a list with 5 elements
'''

def rbox2bbox(rbox):
	ctr = (rbox[0], rbox[1])
	size = (rbox[2], rbox[3])
	angle = rbox[4]
	rrect = (ctr, size, angle)
	contour = cv2.boxPoints(rrect)	
	bbox = cv2.boundingArea(contour)
	return bbox

def rrect2rbox(rrect):
	ctr = rrect[0]
	size = rrect[1]
	angle = rrect[2]
	heading = angle2heading(angle)
	rbox = [ctr[0], ctr[1], size[0], size[1], heading]
	return rbox

# length of hypotenuse via pythagorean theorem
def linelen(pt0, pt3):
	a = pt3[1] - pt0[1]
	b = pt3[0] - pt0[0]
	hyp = math.sqrt(a**2 + b**2)
	return hyp

#def rect2rrect(rect):
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

def angle2heading(angle, which='east'):
	hdg = angle
	rhdg = reverseHeading(hdg)
	if which == 'east':
		return hdg
	elif which == 'west':
		return rhdg
	elif which == 'both':
		return hdg,rhdg

def heading2angle(hdg):
	return hdg

