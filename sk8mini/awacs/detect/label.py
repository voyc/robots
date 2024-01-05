'''
label.py - label management library

a label object is a two-dimensional list of integers, 
one row for each detected object in an image
the first column is the classifier
the next four columns represent the bounding box for cones, or the center box for the sk8
the fifth column is the heading of the sk8, 0 for cones
this list is assumed to have been sorted, ala sorted(label)

Three use cases:
	1. scoring: bbox, cbox+angle
	2. future AI training: unknown, possibly keypoints 
	3. realtime: cone centers, vehicle center and heading

a label object is stored in a .csv file
example filenames:
00001.jpg - the image
00001_label.csv - the label file
00001_truth.csv - a perfected label file, "ground truth", used for training

''' 

import csv

# index the columns of a label list
cls = 0	# clsid 1:cone, 2:sk8
l = 1	# bbox for cone, centerbox for sk8
t = 2
w = 3
h = 4
a = 5  # heading angle
m = 6  # match, used temporarily during scoring
e = 7  # error, used temporarily during scoring

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

# output formats
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

def rbox2bbox(rbox)
	ctr = (rbox[0], rbox[1])
	size = (rbox[2], rbox[3])
	angle = rbox[4]
	rrect = (ctr, size, angle)
	contour = cv2.boxPoints(rrect)	
	bbox = cv2.boundingArea(contour)
	return bbox

def computeHeading(angle):
	heading = angle
	# width, height, and angle returned from cv2.minRectArea() have to be interpreted.

	# The angle returned from minRectArea() is from 0 to -90 degrees, ie, Quadrant IV, 
	# computed from horizontal to the easternmost side of the rotated rectangle.

	# width and height are reversed depending on which side is being used to compute the angle
	# 0 is horizontal, -90 is vertical

	# The animated explanation at https://theailearner.com/tag/cv2-minarearect/
	# would be more helpful if it was rotating counter-clockwise.

	# step 1, determine longest dimension vs shortest dimension 
	# for clsid=2, 'sk8', the long side is the height, the y-dimension
	# the short side is the width, the x-dimension 

	# the direction of travel is the x dimension
	# roll occurs about the y axis

	# convert relative to north=0 or 360

	# orientation systems often used for vehicles, see https://en.wikipedia.org/wiki/Axes_conventions
	# ENU  east, north, up - world frame
	# RPY  roll, pitch, yaw - vehicle body frame

	# longitudinal axis runs from west to east, from tail to nose, assigned to x
	# lateral axis runs from south to north, from right to left, assigned to y

	# unit circle trignometry
	# https://degreespatsuriwa.blogspot.com/2017/09/degrees-quadrant.html
	# http://theo.x10hosting.com/examples/quadrants_1.jpg


	# this is the same system used by minAreaRect(),
	# 0 degrees is horizontal pointing east
	# the direction of travel is along the x axis

	# at 0 degrees, the vehicle is pointing east 
	# the length of the vehicle is measured along the x-axis, an is therefore returned as width
	# the 
	# width is the x axis, the length or longest side of the vehicle
	# height is the y axis, the width or shortest side of the vehicle 
	# therefore width measures the x axis and height measures 

	# heading is at 90 degrees to the computer graphics angle

	# step 1.  fix angle for width and height
	# step 2.  compute the compass heading from the angle, two possible answers
	#             we need to know difference between the nose and the tail of the vehicle
	# 		we could use the comparison with the previous center, but that is inconclusive
	return heading

'''
picture the rectangle on a x,y graph
w is distance along the x axis
h is distance along the y axis

=if(and($C4>=90, $C4<180), 4, 0)
=if(and($C4>=180, $C4<270), 3, 0)
=if(and($C4>=270, $C4<=360), 2, 0)
=if(and($C4>=0, $C4<90), 1, 0)

=if(and($C4>=90, $C4<180), 4, if(and($C4>=180, $C4<270), 3, if(and($C4>=270, $C4<=360), 2, if(and($C4>=0, $C4<90), 1, 0))))



=if($F4=4,0-($C4-90),-1)
=if($F4=3,0-($C4-180),-1)
=if($F4=2,0-($C4-270),-1)
=if($F4=1,0-$C4,-1)

=if($F4=4,0-($C4-90),if($F4=3,0-($C4-180),if($F4=2,0-($C4-270),if($F4=1,0-$C4,-1))))

'''



def correctWidthVsHeight(width,height,angle):
	if width > height:
		w = width
		h = height
		a = angle
	else:
		h = width
		w = height
		a = angle  

	return w,h,a

def convertAngleToHeading(angle):
	heading = angle - 90
	if heading < 0:
		heading = 360 - heading
	return heading

def angle2heading(angle):
	return heading

#heading = a - 90
#if heading < 0:
#	heading = 360 - heading

def heading2angle():
	return angle

def rrect2rbox(rrect):
	ctr = rrect[0]
	size = rrect[1]
	angle = rrect[2]
	heading = angle2heading(angle)
	rbox = [ctr[0], ctr[1], size[0], size[1], heading]
	return rbox

# ------------------- unit test ------------------------- #

def main():
	example_label = [
		[1, 533, 517, 20, 20,   0],
		[1, 186, 407, 27, 21, 180],
		[2, 482, 288,  8, 10, 360],
	]
	s = format(example_label)
	print(f'format\n{s}')

	fname = 'test.csv'

	print('write to file')
	print(example_label)
	write(example_label, fname)

	print('read back in')
	t = read(fname)
	print(t)

if __name__ == '__main__':
	main()

