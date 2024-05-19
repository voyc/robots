'''
score.py - score library

Multiple kinds of scores:

1. error or loss or divergence score.
	An error of zero indicates a perfect match.
	The higher the error, the more divergent the two lists.

2. probability or confidence score.
	A value of 0 between 1.
	A value of 1 indicates total confidence.  A guarantee.
	A value of 0 indicates "not gonna happen".

Uses of scoring:
	During model training, we compare a label list to its corresponding ground-truth list.
	During object detection, we compare a proposed object's detected size to its expected size.

'''
import numpy as np
import copy
import cv2
import math

import label as lbl

penalty_missing = 1000
penalty_extra = 900

#------------------ error/loss functions, low score is better -----------

# mean squared error
def calcMSE(predicted, actual):
	actual = np.array(actual) 
	predicted = np.array(predicted) 
	differences = np.subtract(actual, predicted)
	squared_differences = np.square(differences)
	mean = squared_differences.mean()
	return mean

# root mean squared error
def calcRMSE(predicted, actual):
	mse = calcMSE(predicted, actual)
	rmse = math.sqrt(mse)
	return rmse

# intersection over union
def calcIOU(predicted, actual):
	iou = 0
	return iou

#------------------ probability, high score is better -----------

# probability: 0/1, confidence score, 1 is certain, 0 is never
def calcProbability(error, maxerror):
	return 1 - (error / maxerror)

#---------------------------------------------------------------

# match each truth object to one detect object, by scoring all possible pairs
def matchup(truth,detect):
	# compare two lists, and return mse
	def compareRows(a,b):
		return calcMSE(a[lbl.cx:lbl.m], b[lbl.cx:lbl.m])

	if not len(detect):
		return 0, float('inf'), {}

	# add two cells to all rows, m for match, e for error
	for trow in truth:
		trow.append(0)
		trow.append(-1)
	for arow in detect:
		arow.append(0)
		arow.append(penalty_extra)

	# match, nested loops
	tndx = 0
	for trow in truth:
		tndx += 1
		andx = 0
		for arow in detect:
			andx += 1
			if arow[lbl.cls] == trow[lbl.cls]:
				mse = compareRows(trow,arow)
				if mse < trow[lbl.e] or trow[lbl.e] < 0: 
					trow[lbl.m] = andx
					trow[lbl.e] = mse
					# arow[m] = tndx  # this don't work, do reverse match instead

	# reverse match
	tndx = 0
	for trow in truth:
		tndx += 1
		if trow[lbl.m] > 0:
			detect[trow[lbl.m]-1][lbl.m] = tndx
			detect[trow[lbl.m]-1][lbl.e] = trow[lbl.e]

	# replace dupes, ie missing
	struth = sorted(truth, key=lambda a: [a[lbl.m], a[lbl.e]])	
	save = -1
	for srow in struth:
		if save == srow[lbl.m]:
			srow[lbl.m] = 0 # no match
			srow[lbl.e] = penalty_missing
		else:
			save = srow[lbl.m]

	# array of cls values in the truth
	acls = {}
	for t in truth:
		acls[t[lbl.cls]] = 0
	
	# total error for all objects in truth
	error = 0
	for trow in truth:
		error += trow[lbl.e]
		acls[trow[lbl.cls]] += trow[lbl.e]

	# plus extras in detect
	for arow in detect:
		if arow[lbl.m] == 0:
			error += arow[lbl.e]
#			acls[arow[c]] += arow[e]   # ?

#	# calc means
#	for cls in acls:
#		err = acls[lbl.cls]
#		acls[lbl.cls] = [err, int(err / len(truth))]

	#mean = int(error / len(truth))
	return error
	return error, mean, acls


def scoreLabelsAgainstTruth(truthset, labelset, maxerror=1000):
	truth = truthset[0]
	label = labelset[0]
	rmse = calcRMSE(truth[lbl.cx:lbl.scr], label[lbl.cx:lbl.scr])
	pscore = calcProbability(rmse,maxerror)
	clscores = [0,1,2,3]
	scoredlabelset = labelset
	for label in scoredlabelset:
		label[lbl.scr] = pscore
	return rmse, pscore, clscores, scoredlabelset


