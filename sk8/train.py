''' train.py - sk8 trainer '''

import os
import numpy as np
import cv2 as cv
import copy
import sk8mat as sm
import universal as uni
import visualcortex as vc

def readTarget(tname,ddim):
	fh = open(tname)
	tdata = fh.readlines()
	target = []
	for line in tdata:
		a = line.split(' ')
		cls = int(a.pop(0))
		a = list(np.array(a).astype(float)) 
		l,t,w,h = a
		box = sm.Box((l,t), [w,h])
		edge = sm.Edge(cls,box)
		edge.toD(ddim)
		target.append(edge)
	return target

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
			return 0
		a = boxa.pbox.ltwh()
		g = boxg.pbox.ltwh()
		e = np.array(g) - np.array(a)
		print('a', a)
		print('g', g)
		print('e', e)
		e = 100 * e
		se = e ** 2 
		sse = np.sum(se)
		return sse

	# matchup # 1,2,3 are easy
	ssea = [0,0,0,0]
	for cls in range(0,4):
		a = getBoxByCls(attempt,cls)
		g = getBoxByCls(goal,cls)
		e = diff(a,g)
		ssea[cls] += e

	#a = getSetByCls(attempt,0)
	#g = getSetByCls(goal,0)
	# do cones
	return ssea
	
def onetest(threshholds):
	sse = np.array([0.,0.,0.,0.])

	# find last framenum
	filelist = os.listdir( dirframe)
	lastfnum = len(filelist)
	
	# read jpg files in numeric order
	for fnum in range(1,lastfnum+1):
		fname = f'{dirframe}/{fnum}.jpg'
		frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
		h,w,d = frame.shape
		ddim = [w,h]
	
		tname = f'{dirtrain}/{fnum}.txt'
		targetboxes = readTarget(tname,ddim)
	
		testboxes = visualcortex.detectObjects(frame, threshholds)
		e = score(testboxes, targetboxes)
		sse += np.array(e)
		print(fnum)
		print(e)
		print(sse)
		print(len(testboxes))
		print(len(targetboxes))

	return sse

class Ta:
	def __init__(self,cls,threshholds):
		self.cls = cls 
		self.sse = 0                                 # sum of squared error
		self.psse = float('inf')                     # previous best sse
		self.a = threshholds[cls]                    # pointer to threshholds for this class
		self.pa = copy.deepcopy(self.a)              # previous best threshholds
		self.d = [1,-1,1,-1,1,-1,1,-1,2,1]           # direction to tweak
		self.m = [179,0,255,0,255,0,255,0,255,255]   # max tweak
		self.i = 0                                   # index into a
		self.mi = 9                                  # max index
		self.state = 'working' # or 'finished'

	def unpack(self):
		return self.a  # hl,hu,sl,su,vl,vu,cl,cu,gk,gs

	def pack(self,a):
		self.a = a  # [hl,hu,sl,su,vl,vu,cl,cu,gk,gs]
	
	def tweak(self,sse):
		if self.state == 'finished':
			return
		self.sse = sse
		if self.sse <= self.psse:                # if latest has lower error
			self.pa = copy.deepcopy(self.a)  # keep it
			self.psse = self.sse
			self.incrt()                     # increment t, keep going
		else:                                    # else, if latest is worse
			self.a = copy.deepcopy(self.pa)  # restore the previous
			self.sse = self.psse
			self.nextt()                     # move on to next t

	def incrt(self):
		self.a[self.i] += self.d[self.i]

	def nextt(self):
		self.i += 1                  # move on to the next t
		if self.i >= self.mi:        # unless that was the last t
			self.state = 'finished'
		else:
			self.incrt()

	def isFinished(self):
		return self.state == 'finished'

	def __str__(self):
		return f'Ta {self.cls} {self.sse} {self.a}'

def isFinished():
	cnt = 0
	for cls in range(0,4):
		if taa[cls].isFinished():
			cnt += 1
	return cnt >= 4

dir = '/home/john/sk8/bench/train'
dirframe = f'{dir}/frame'
dirtrain = f'{dir}/train'
visualcortex = vc.VisualCortex()
threshholds = vc.Detect.threshhold_seeds

if True:
	ddim = [960,720]
	fnum = 3
	tname = f'{dirtrain}/{fnum}.txt'
	targets = readTarget(tname,ddim)
	print(*targets, sep='\n')
	
	fname = f'{dirframe}/{fnum}.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	tests = visualcortex.detectObjects(frame, threshholds)
	print(*tests, sep='\n')
	
	sse = score(tests,targets)
	quit()
	
	sse = onetest(threshholds)
	print('sse', sse)

print(*threshholds, sep='\n')
taa = []
for cls in range(0,4):
	taa.append(Ta(cls,threshholds))
taa[0].state = 'finished'
#taa[2].state = 'finished'
#taa[3].state = 'finished'

while not isFinished():
	sse = onetest(threshholds)
	for cls in range(0,4):
		taa[cls].tweak(sse[cls])      # review the score and tweak the threshholds accordingly
	#print(*taa, sep='\n')
print(*threshholds, sep='\n')
'''
onetest() runs thru all frames in the training data, for one set of threshholds

onetest returns an sse for each cls

three arrays, with four elements, one for each class
	threshholds[cls]
	sse[cls]                          
	taa[cls]

output is the optimal set of threshholds
'''
