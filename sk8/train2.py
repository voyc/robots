''' train.py - sk8 trainer '''

import os
import numpy as np
import cv2 as cv
import copy
import sk8mat as sm
import universal as uni
import visualcortex as vc

class TestState:
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
		return f'TestState {self.cls} {self.sse} {self.a}'

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
			return max_error
		a = boxa.dbox.ltrb()
		g = boxg.dbox.ltrb()
		e = np.array(g) - np.array(a)
		se = e ** 2 
		sse = np.sum(se)
		return sse

	# compare padl, padr, spot
	ssea = [0,0,0,0]
	for cls in range(1,4):
		a = getBoxByCls(attempt,cls)
		g = getBoxByCls(goal,cls)
		e = diff(a,g)
		ssea[cls] += e

	# compare cones
	cls = 0
	a = getSetByCls(attempt,cls)
	g = getSetByCls(goal,cls)
	d = len(a) - len(g)
	if d > 0:
		ssea[cls] += d * 100
	for n in range(0,len(g)):
		e = diff(a[n],g[n])
		ssea[cls] += e
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

def isFinished(tsa):
	cnt = 0
	for cls in range(0,4):
		if tsa[cls].isFinished():
			cnt += 1
	return cnt >= 4

def initializeTrainingSet():
	# read all frames and target boxes
	frames = []
	targetboxes = []
	num = 0
	while True:
		fnum = num+1
		fname = f'{dirframe}/{fnum}.jpg'
		f = cv.imread( fname, cv.IMREAD_UNCHANGED)
		if f is None:
			break
		frames.append(f)
		tname = f'{dirtrain}/{fnum}.txt'
		targetboxes.append( readTarget(tname,ddim))
		num += 1
	return frames, targetboxes

def testoneset(frames, targetboxes):
	numframes = len(frames)
	sse = np.array([0,0,0,0])
	for num in range(0,numframes):
		fnum = num+1
		testboxes = visualcortex.detectObjects(frames[num], threshholds)
		e = score(testboxes, targetboxes[num])
		print(f'frame {fnum}: {e}')
		sse += np.array(e)
	print('total', sse)
	mse = (sse / numframes).astype(int)
	print('mean', mse)
	return mse

# globals
dir = '/home/john/sk8/bench/train'
dirframe = f'{dir}/frame'
dirtrain = f'{dir}/train'
visualcortex = vc.VisualCortex()
threshholds = vc.Detect.threshhold_seeds
ddim = [960,720]
max_error = 1000
print(f'starting threshholds:')
print(*threshholds, sep='\n')

# global training set
frames, targetboxes = initializeTrainingSet()
numframes = len(frames)
print(f'training set initialized: {numframes} frames')

# global test state array
tsa = []
for cls in range(0,4):
	tsa.append(TestState(cls,threshholds))

# start testing
testnum = 1
while not isFinished(tsa):
	mse = testoneset(frames, targetboxes)

	for cls in range(0,4):
		tsa[cls].tweak(mse[cls])      # review the score and tweak the threshholds accordingly
	break













quit()

tests = visualcortex.detectObjects(frames[fnum], threshholds)
print(*tests, sep='\n')

sse = score(tests,targets)
quit()

sse = onetest(threshholds)
print('sse', sse)

print(*targets, sep='\n')

print(*threshholds, sep='\n')
taa = []
for cls in range(0,4):
	taa.append(TestState(cls,threshholds))
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
