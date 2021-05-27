''' train.py - sk8 trainer '''

import os
import numpy as np
import cv2 as cv
import copy
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

threshhold_max = [ 
	# class          hue      sat      val     canny
	( uni.clsCone,   0,179,  42,100,  35,100,  82,127 ),
	( uni.clsPadl,   0,179,  42,100,  10, 90,  82,127 ),
	( uni.clsPadr,   0,179,  24, 76,  10, 90,  82,127 ),
	( uni.clsSpot,   0,179,  46,100,  10, 90,  82,127 )
]

ta = [
	
class Ta:
	def __init__(self,cls):
		self.cls = cls 
		self.sse = 0                                 # sum of squared error
		self.psse = 0                                # previous sse
		#self.a = [0,179,0,255,0,255,0,255,1,0]       # array of t, as in threshhold
		self.a = threshholds[cls]
		self.pa = []                                 # previous a
		self.d = [1,-1,1,-1,1,-1,1,-1,2,1]           # direction to tweack
		self.m = [179,0,255,0,255,0,255,0,255,255]   # max tweak
		self.i = 0                                   # index into a
		self.mi = 9                                  # max index

	def unpack(self):
		return self.a  # hl,hu,sl,su,vl,vu,cl,cu,gk,gs

	def pack(self,a):
		self.a = a  # [hl,hu,sl,su,vl,vu,cl,cu,gk,gs]
	
	def tweak(self,sse):
		if sse < self.psse:                      # if latest result is better
			self.pa = copy.deepcopy(self.a)  # save to previous set
			self.incrt()                     # increment t
		else:                                    # if latest result is worse
			self.a = copy.deepcopy(self.pa)  # back up to previous set
			self.nextt()                     # move on to next t
		return True

	def incrt(self):
		self.a[self.i] += self.d[self.i]

	def nextt(self):
		if self.a[self.i] == self.m[self.i]: # if t is already at its max
			self.i++                     # move on to the next t
			if self.i >= self.mi:        # unless that was the last t
				return False         # finished
		else:                                # otherwise
			pass          	             # no change	
		return True

def tweak(sse, threshholds):
 
	newthreshholds = copy.deepcopy(threshholds)
	for cls in range(0,4):
		_,hl,hu,sl,su,vl,vu,cl,cu = newthreshholds[cls]
		hl += 1
		hu -= 1
		newthreshholds[cls] = (cls,hl,hu,sl,su,vl,vu,cl,cu)
	if hu < 0: return False
	return newthreshholds

def descent(threshholds):
	newthreshholds = copy.deepcopy(threshholds)

	while newthreshholds:
		sse = onetest(newthreshholds)
		for hold in newthreshholds: print(hold, sse[hold[0]])

		newthreshholds = tweak(sse, newthreshholds)

	return newthreshholds

# begin here
visualcortex = vc.VisualCortex()
#oldthreshholds = vc.Detect.threshhold_max
#newthreshholds = descent(oldthreshholds)

ta = []
for cls = range(0,4):
	ta[cls] = Ta(cls)

while True:
	for cls = range(0,4):
		hl,hu,sl,su,vl,vu,cl,cu,gk,gs = ta[cls].unpack()

