'''
score.py - score library,  compare two detection lists

the output score is a mean squared error
a score of zero indicates a perfect match
the higher the score, the more divergent the two lists

during model training, we compare a detection list to its corresponding training list
'''

import numpy as np
import copy
import cv2
import detection

penalty_missing = 1000
penalty_extra = 900

# index the columns of a detection list
c   = 0  # cls id
cx  = 1  # center pt
cy  = 2
ra  = 3  # radius for cones, angle for sk8 

l   = 4  # bounding box
t   = 5
w   = 6  # size
h   = 7

m   = 8
e   = 9

ltx =10  # four points of rotated rectangle returned from cvs.boxPoints()
lty =11
rtx =12
rty =13
rbx =14
rby =15
lbx =16
lby =17
wd  =18  # rotated size 
ht  =19
ang =20  # angle

def computeHeading():
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

	longitudinal axis runs from west to east, from tail to nose, assigned to x
	lateral axis runs from south to north, from right to left, assigned to y

	# unit circle trignometry
	# https://degreespatsuriwa.blogspot.com/2017/09/degrees-quadrant.html
	# http://theo.x10hosting.com/examples/quadrants_1.jpg


	this is the same system used by minAreaRect(),
	0 degrees is horizontal pointing east
	the direction of travel is along the x axis

	at 0 degrees, the vehicle is pointing east 
	the length of the vehicle is measured along the x-axis, an is therefore returned as width
	the 
	width is the x axis, the length or longest side of the vehicle
	height is the y axis, the width or shortest side of the vehicle 
	therefore width measures the x axis and height measures 

	heading is at 90 degrees to the computer graphics angle

	# step 1.  fix angle for width and height
	# step 2.  compute the compass heading from the angle, two possible answers
	#             we need to know difference between the nose and the tail of the vehicle
	# 		we could use the comparison with the previous center, but that is inconclusive

def correctWidthVsHeight(width,height,angle):
	if width > height:
		w = width
		h = height
		a = angle
	else:
		h = width
		w = height
		a = angle  

at 0 
	
	return w,h,a

def convertAngleToHeading(angle):
	heading = angle - 90
	if heading < 0:
		heading = 360 - heading
	return heading

# calc mean squared error using numpy vector math
def mseVector(predicted, actual):
	actual = np.array(actual) 
	predicted = np.array(predicted) 
	differences = np.subtract(actual, predicted)
	squared_differences = np.square(differences)
	mean = squared_differences.mean()
	return mean

# match each train object to one detect object, by scoring all possible pairs
def matchup(train,detect):
	# compare two lists, and return mse
	def compareRows(hoo,hah):
		return int(mseVector(hoo[cx:l], hah[cx:l]))
		return int(mseVector(hoo[l:m], hah[l:m]))

	if not len(detect):
		return 0, float('inf'), {}

	# add two cells to all rows, m for match, e for error
	for trow in train:
		trow.append(0)
		trow.append(-1)
	for arow in detect:
		arow.append(0)
		arow.append(penalty_extra)

	# match, nested loops
	tndx = 0
	for trow in train:
		tndx += 1
		andx = 0
		for arow in detect:
			andx += 1
			if arow[c] == trow[c]:
				mse = compareRows(trow,arow)
				if mse < trow[e] or trow[e] < 0: 
					trow[m] = andx
					trow[e] = mse
					# arow[m] = tndx  # this don't work, do reverse match instead

	# reverse match
	tndx = 0
	for trow in train:
		tndx += 1
		if trow[m] > 0:
			detect[trow[m]-1][m] = tndx
			detect[trow[m]-1][e] = trow[e]

	# replace dupes, ie missing
	strain = sorted(train, key=lambda a: [a[m], a[e]])	
	save = -1
	for srow in strain:
		if save == srow[m]:
			srow[m] = 0 # no match
			srow[e] = penalty_missing
		else:
			save = srow[m]

	# array of cls values in the train
	acls = {}
	for t in train:
		acls[t[c]] = 0
	
	# total error for all objects in train
	error = 0
	for trow in train:
		error += trow[e]
		acls[trow[c]] += trow[e]

	# plus extras in detect
	for arow in detect:
		if arow[m] == 0:
			error += arow[e]
#			acls[arow[c]] += arow[e]   # ?

	# calc means
	for cls in acls:
		err = acls[cls]
		acls[cls] = [err, int(err / len(train))]

	mean = int(error / len(train))
	return error, mean, acls


#------------------- unit test ----------------------------#

def draw(img, train, detect):
	imgMap = img.copy()
	for trow in train:
		# draw the training object as green ring, or blue if not matched
		thickness = 1
		color = (  0,255,  0) 
		if trow[m] == 0:
			color = (255,  0,  0) 
		x = trow[l]+int(trow[w]/2)
		y = trow[t]+int(trow[w]/2)
		r = 10
		#imgMap = cv2.circle(imgMap, (trow[x],trow[y]), int(trow[r]/2), color, thickness) 
		imgMap = cv2.circle(imgMap, (x,y), r, color, thickness) 

		# draw the detect object as pink box, or red if extra
		if trow[m] < len(detect):
			arow = detect[trow[m]-1]
		color = (128,128,255) 
		al = arow[l]
		at = arow[t]
		aw = arow[w]
		ah = arow[h]
		imgMap = cv2.rectangle(imgMap, (al,at), (al+aw,at+ah), color, thickness) 

		# draw the score of matched and unmatched training objects
		s = f'{trow[e]}'
		color = (  0,  0,  0) 
		cv2.putText(imgMap, s, (x-20,y-20), cv2.FONT_HERSHEY_PLAIN, 1, color)

	# now draw the extras
	color = (  0,  0,255) 
	for arow in detect:
		if arow[m] == 0:
			al = arow[l]
			at = arow[t]
			aw = arow[w]
			ah = arow[h]
			imgMap = cv2.rectangle(imgMap, (al,at), (al+aw,at+ah), color, thickness) 
			s = f'{arow[e]}'
			color = (  0,  0,  0) 
			cv2.putText(imgMap, s, (al-20,at), cv2.FONT_HERSHEY_PLAIN, 1, color)

	return imgMap

# one training set and three tests
imagefname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095.jpg'
#trainfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_train.csv'
#equalfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_equal.csv'
#shortfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_short.csv'
#extrafname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_extra.csv'
#closefname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_close.csv'
#testrfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_testr.csv'

train = [
[1,  88, 526, 19,  78, 517, 20, 18], 
[1,  98,  59, 21,  87,  49, 22, 20],
[1, 199, 417, 19, 190, 408, 19, 19],
[1, 199, 177, 18, 191, 168, 17, 19],
[1, 301, 299, 18, 291, 291, 20, 17],
[1, 407, 185, 20, 396, 176, 22, 19],
[1, 416, 410, 20, 406, 400, 21, 20],
[1, 538, 529, 30, 522, 515, 32, 29],
[1, 540,  55, 25, 527,  43, 26, 25],
[2, 429, 157,  7, 426, 153,  6,  9],
[2, 447, 170, 13, 442, 163, 11, 15],
[2, 458, 125, 12, 452, 119, 12, 13],
[2, 479, 155, 14, 472, 149, 15, 13],
[3, 441, 151, 29, 427, 136, 29, 30] 
]
detect_equal = [
[1,  88, 526, 19,  78, 517, 20, 18], 
[1,  98,  59, 21,  87,  49, 22, 20],
[1, 199, 417, 19, 190, 408, 19, 19],
[1, 199, 177, 18, 191, 168, 17, 19],
[1, 301, 299, 18, 291, 291, 20, 17],
[1, 407, 185, 20, 396, 176, 22, 19],
[1, 416, 410, 20, 406, 400, 21, 20],
[1, 538, 529, 30, 522, 515, 32, 29],
[1, 540,  55, 25, 527,  43, 26, 25],
[2, 429, 157,  7, 426, 153,  6,  9],
[2, 447, 170, 13, 442, 163, 11, 15],
[2, 458, 125, 12, 452, 119, 12, 13],
[2, 479, 155, 14, 472, 149, 15, 13],
[3, 441, 151, 29, 427, 136, 29, 30] 
]
detect_close = [
[1, 104, 537, 22,  92, 527, 23, 21],
[1,  82,  74, 12,  75,  69, 13, 11],
[1, 201, 405, 22, 189, 394, 22, 22],
[1, 209, 177, 18, 200, 168, 17, 19],
[1, 295, 290, 25, 281, 278, 27, 24],
[1, 407, 185, 20, 395, 176, 22, 19],
[1, 416, 418, 20, 405, 408, 21, 20],
[1, 542, 531, 28, 526, 518, 30, 27],
[1, 539,  53, 29, 523,  39, 30, 29],
[2, 427, 159, 11, 421, 153, 10, 13],
[2, 446, 169, 10, 441, 163,  8, 12],
[2, 459, 124, 14, 451, 117, 14, 15],
[2, 483, 155, 17, 473, 147, 18, 16],
[3, 442, 142, 22, 430, 131, 22, 23] 
]

detect_testr = [
[1, 104, 537, 22,  93, 527, 23, 21], 
[1,  82,  74, 12,  76,  69, 13, 11], 
[1, 201, 405, 22, 190, 394, 22, 22], 
[1, 209, 177, 18, 201, 168, 17, 19], 
[1, 295, 290, 25, 282, 278, 27, 24], 
[1, 241, 260, 18, 231, 252, 20, 17], 
[1, 407, 185, 20, 396, 176, 22, 19], 
[1, 416, 418, 20, 406, 408, 21, 20], 
[1, 542, 531, 28, 527, 518, 30, 27], 
[1, 539,  53, 29, 524,  39, 30, 29], 
[2, 427, 159, 11, 422, 153, 10, 13], 
[2, 446, 169, 10, 442, 163,  8, 12], 
[2, 483, 155, 17, 474, 147, 18, 16], 
[3, 442, 142, 22, 431, 131, 22, 23]
]
detect_short = [
[1,  88, 526, 19,  78, 517, 20, 18],
[1,  98,  59, 21,  87,  49, 22, 20],
[1, 199, 417, 19, 190, 408, 19, 19],
[1, 199, 177, 18, 191, 168, 17, 19],
[1, 407, 185, 20, 396, 176, 22, 19],
[1, 416, 410, 20, 406, 400, 21, 20],
[1, 538, 529, 30, 522, 515, 32, 29],
[1, 540,  55, 25, 527,  43, 26, 25],
[2, 429, 157,  7, 426, 153,  6,  9],
[2, 447, 170, 13, 442, 163, 11, 15],
[2, 458, 125, 12, 452, 119, 12, 13],
[2, 479, 155, 14, 472, 149, 15, 13],
[3, 441, 151, 29, 427, 136, 29, 30]
]
detect_extra = [
[1,  88, 526, 19,  78, 517, 20, 18],
[1,  98,  59, 21,  87,  49, 22, 20],
[1, 199, 417, 19, 190, 408, 19, 19],
[1, 199, 177, 18, 191, 168, 17, 19],
[1, 301, 299, 18, 291, 291, 20, 17],
[1, 361, 303, 18, 351, 295, 20, 17],
[1, 407, 185, 20, 396, 176, 22, 19],
[1, 416, 410, 20, 406, 400, 21, 20],
[1, 538, 529, 30, 522, 515, 32, 29],
[1, 540,  55, 25, 527,  43, 26, 25],
[2, 429, 157,  7, 426, 153,  6,  9],
[2, 447, 170, 13, 442, 163, 11, 15],
[2, 458, 125, 12, 452, 119, 12, 13],
[2, 479, 155, 14, 472, 149, 15, 13],
[3, 441, 151, 29, 427, 136, 29, 30]
]

def calcCenter(row):
	row[cx] = int(row[l] + (row[w]/2))
	row[cy] = int(row[t] + (row[h]/2))
	row[ra] = int((row[w] + row[h])/2)

def matchone(name):
	test_train = copy.deepcopy(train)
	test_detect = copy.deepcopy(globals()[name])

	error, mean, acls = matchup(test_train,test_detect)
	print(f'{name}: {error}, {mean}')

def main():
	matchone('detect_equal')
	matchone('detect_close')
	matchone('detect_testr')
	matchone('detect_short')
	matchone('detect_extra')
	quit()

	#print(detection.format(detect_equal))
	#img = cv2.imread(imagefname, cv2.IMREAD_UNCHANGED)
	#imgMap = draw(img, train, detect)
	#cv2.imshow('matched', imgMap)
	#cv2.waitKey(0) # wait indefinitely for keystroke

if __name__ == '__main__':
	main()

