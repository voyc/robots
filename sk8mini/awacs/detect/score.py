'''
score.py - score library,  compare two label lists

the output score is a mean squared error
a score of zero indicates a perfect match
the higher the score, the more divergent the two lists

during model training, we compare a label list to its corresponding truth list
'''

import numpy as np
import copy
import cv2

import label as lab

penalty_missing = 1000
penalty_extra = 900

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
	def compareRows(a,b):
		return int(mseVector(a[lab.cx:lab.m], b[lab.cx:lab.m]))

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
			if arow[lab.cls] == trow[lab.cls]:
				mse = compareRows(trow,arow)
				if mse < trow[lab.e] or trow[lab.e] < 0: 
					trow[lab.m] = andx
					trow[lab.e] = mse
					# arow[m] = tndx  # this don't work, do reverse match instead

	# reverse match
	tndx = 0
	for trow in train:
		tndx += 1
		if trow[lab.m] > 0:
			detect[trow[lab.m]-1][lab.m] = tndx
			detect[trow[lab.m]-1][lab.e] = trow[lab.e]

	# replace dupes, ie missing
	strain = sorted(train, key=lambda a: [a[lab.m], a[lab.e]])	
	save = -1
	for srow in strain:
		if save == srow[lab.m]:
			srow[lab.m] = 0 # no match
			srow[lab.e] = penalty_missing
		else:
			save = srow[lab.m]

	# array of cls values in the train
	acls = {}
	for t in train:
		acls[t[lab.cls]] = 0
	
	# total error for all objects in train
	error = 0
	for trow in train:
		error += trow[lab.e]
		acls[trow[lab.cls]] += trow[lab.e]

	# plus extras in detect
	for arow in detect:
		if arow[lab.m] == 0:
			error += arow[lab.e]
#			acls[arow[c]] += arow[e]   # ?

#	# calc means
#	for cls in acls:
#		err = acls[lab.cls]
#		acls[lab.cls] = [err, int(err / len(train))]

	#mean = int(error / len(train))
	return error
	return error, mean, acls

