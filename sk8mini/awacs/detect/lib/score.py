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

# index the cells of each row in a detection
c=0
l=1
t=2
w=3
h=4
m=5
e=6
#x=5
#y=6
#r=7
#m=8
#e=9

# match each train object to one detect object, by scoring all possible pairs
def match(train,detect):
	# calc mean squared error using numpy vector math
	def mseVector(predicted, actual):
		actual = np.array(actual) 
		predicted = np.array(predicted) 
		differences = np.subtract(actual, predicted)
		squared_differences = np.square(differences)
		mean = squared_differences.mean()
		return mean
	
	# compare two lists, and return mse
	def compareRows(t,a):
		return int(mseVector(t[l:m], a[l:m]))

	if not len(detect):
		return float('inf')

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
			acls[arow[c]] += arow[e]

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
trainfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_train.csv'
equalfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_equal.csv'
shortfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_short.csv'
extrafname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_extra.csv'
closefname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_close.csv'
testrfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/00095_detect_testr.csv'

detectfname = testrfname


#tt = [1, 527, 43, 26, 25, 540, 55, 25]
#ta = [1, 529, 45, 22, 22, 540, 56, 22]

def main():
	train = detection.read(trainfname)
	s = detection.format(train)
	print(f'train before\n{s}')

	detect = detection.read(detectfname)
	s = detection.format(detect)
	print(f'detect before\n{s}')
	
	# compare
	error, mean, acls = match(train,detect)
	print(f'error: {error}, mean: {mean}')
	print(acls)
	
	s = detection.format(train)
	print(f'train after\n{s}')
	s = detection.format(detect)
	print(f'detect after\n{s}')

	img = cv2.imread(imagefname, cv2.IMREAD_UNCHANGED)
	imgMap = draw(img, train, detect)
	cv2.imshow('matched', imgMap)
	cv2.waitKey(0) # wait indefinitely for keystroke

if __name__ == '__main__':
	main()

