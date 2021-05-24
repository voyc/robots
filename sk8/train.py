''' train.py - sk8 trainer '''

import os
import numpy as np
import cv2 as cv
import visualcortex as vc
import sk8math

dir = '/home/john/sk8/bench/train'
dirframe = f'{dir}/frame'
dirtrain = f'{dir}/train'

def readBoxes(tname,pxldim):
	fh = open(tname)
	tdata = fh.readlines()
	boxes = []
	for line in tdata:
		a = line.split(' ')
		cls = int(a.pop(0))
		a = list(np.array(a).astype(float)) 
		l,t,w,h = a
		bbox = sk8math.Box(cls, (l,t), [w,h])
		bbox.toPxl(pxldim)
		boxes.append(bbox)
	return boxes

def score(attempt,goal):
	def getBoxByCls(boxset, cls):
		for box in boxset:
			if box.cls == cls:
				return box

	def getSetByCls(boxset, cls):
		set = []
		for box in boxset:
			if box.cls == cls:
				set.append(box)
		return set

	def diff(boxa,boxg):
		if boxa is None or boxg is None:
			return 100  # maximum error
		a = boxa.pct_ltwh()
		g = boxg.pct_ltwh()
		e = np.array(g) - np.array(a)
		se = e * 1000000
		se = se ** 2 
		se /= 100000
		sse = np.sum(se)
		return sse

	# matchup # 1,2,3 are easy
	ssea = [0,0,0,0]
	for cls in range(1,4):
		a = getBoxByCls(attempt,cls)
		g = getBoxByCls(goal,cls)
		e = diff(a,g)
		ssea[cls] += e

	a = getSetByCls(attempt,0)
	g = getSetByCls(goal,0)
	# do cones

	return ssea
	
def onetest(settings):
	sse = np.array([0.,0.,0.,0.])

	# find last framenum
	filelist = os.listdir( dirframe)
	lastfnum = len(filelist)
	
	# read jpg files in numeric order
	for fnum in range(1,lastfnum+1):
		fname = f'{dirframe}/{fnum}.jpg'
		frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
		h,w,d = frame.shape
		pxldim = [w,h]
	
		tname = f'{dirtrain}/{fnum}.txt'
		targetboxes = readBoxes(tname,pxldim)
	
		testboxes = visualcortex.detectObjects(frame, settings)
		#for box in testboxes: print(box.write())
		e = score(testboxes, targetboxes)
		sse += np.array(e)

	return sse

# begin here
visualcortex = vc.VisualCortex()
settings = vc.Detect.threshhold_seeds
sse = onetest(settings)
print(sse)

