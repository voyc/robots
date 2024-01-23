'''
sim.py - simulate the camera

comparison of awacs.py and sim.py

awacs.py - realtime camera and object detection
	looper()
		getOptions() from http
		getFrame() from cam
		detectObjects()
		send labelset to vehicle

sim.py - offline 
	looper()
		getOptions() from argparse
		getFrame() from disk
		detectObjects()
		manual frame navigation
			show nth
			pause, forward, back, speedup, slowdown
			write labelset to disk

separate programs, all based on sim.py
	awacs.py - get frame from cam, all manual options removed
	nudge.py - read and modify a labelset
	tweak.py - read and modify a model using trackbars
	train.py - read and modify a model repeatedly until confidence score is maximized
	score.py - read labelset and truthset, compare, and print scores

with separate programs
	everytime I change sim, I have to change it in 5 files

with options all packed into sim
	program can get unmanageable
	change for one option can trigger modifications to all other options

first lets streamline sim.py, implement convex hull algorithms

'''
import cv2
import numpy as np
import os
import argparse
import copy
import logging

import detect
import draw
import frame as frm 
import score as scr
import label as lbl

# global variables
gargs = None     # fixed constants set at startup
gframendx = -1   # used by getFnum() only
gframelist = []  # used by getFnum() only
gfnum = ''  # temp debugging

def getFnum(increment, loop=False):
	global gframendx, gframelist
	if gframendx == -1:
		gframelist = frm.getFrameList(gargs.idir)
	gframendx += increment
	if gframendx >= len(gframelist):
		if loop:
			gframendx = 0
		else:
			return None
	if gframendx < 0:
		gframendx = len(gframelist)-1
	fnum = gframelist[gframendx]
	return fnum

def getFrame(increment):
	fnum = getFnum(increment)
	if not fnum:
		return None, None
	fnum = gframelist[gframendx]
	frame = cv2.imread(frm.fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
	return frame,fnum

# an object detection algorithm
def diffFrames(current,previous):
	imgDiff1 = cv2.absdiff(current, previous)	
	imgDiff2 = cv2.absdiff(current, imgDiff1)
	imgDiff3 = cv2.absdiff(previous, imgDiff2)
	return imgDiff3

def printObjectArray(objarray):
	for obj in objarray:
		print(obj)
	
def findSequenceBreaks(means):
	sortedmeans = sorted(means)
	meanobjs = [{'mean':sortedmeans[0], 'interval':0, 'pct':0}]
	prevmean = 0
	for mean in sortedmeans:
		interval = mean - prevmean 
		if prevmean > 0:
			meanobj = {'mean':mean, 'interval':interval, 'pct':0}
			meanobjs.append(meanobj)
		prevmean = mean
	
	sortedmeanobjs = sorted(meanobjs,  key=lambda a: a['interval'])
	printMeanObjects(sortedmeanobjs)

	bigjump = sortedmeanobjs[len(sortedmeanobjs)-2]
	bpoint = bigjump['mean']

	if bpoint <= 0:
		breakpoint()

	logging.debug(f'findSequenceBreaks bigjump:{bigjump}, bpoint:{bpoint}')
	return bpoint
		
def findBreakPct(apts):
  	# input array of {'ctr':ctr, 'distances':distances, 'mean':mean}

	homethreshold = 5

	# sort by mean
	apts = sorted(apts,  key=lambda a: a['mean'])

	# calc pct
	homepts = []
	prevmean = apts[0]['mean']
	pct = 1
	for pt in apts:
		if prevmean > 0:
			pct = ((pt['mean'] - prevmean) / prevmean) * 100 
			pct = max(pct,1)
		pt['pct'] = pct
		prevmean = pt['mean']

	#	if pct > homethreshold:
	#		homepts.append(pt['ctr'])
	
	# find proposed center of homepts
	#homepts = np.array(homepts)
	#proctr = (np.mean(homepts[:,0]),np.mean(homepts[:,1]))
	#logging.debug(f'proctr: {proctr}')

	# sort by pct 
	apts = sorted(apts,  key=lambda a: a['pct'])
	printObjectArray(apts)
	
	# choose breakpoint as greatest pct jump between points
	maxapt = apts[len(apts)-1]
	bpoint = maxapt['mean']

	# debug: sort by mean
	apts = sorted(apts,  key=lambda a: a['mean'])
	printObjectArray(apts)

	return bpoint

def findBreakVehicle(apts):
  	# input array of {'ctr':ptA, 'distances':distances, 'mean':mean}

	# sort by mean
	apts = sorted(apts,  key=lambda a: a['mean'])

	# calc interval
	prevmean = 0
	for pt in apts:
		interval = pt['mean'] - prevmean 
		pt['interval'] = interval
		prevmean = pt['mean']
	
	# sort by interval
	apts = sorted(apts,  key=lambda a: a['interval'])
	printObjectArray(apts)

	# find center of first five points with the shortest mean distances
	ctr5 = []
	for pt in apts:
		ctr5.append(pt['ctr'])
		if len(ctr5) >= 5:
			break
	ctr5 = np.array(ctr5)
	proposedctr = (np.mean(ctr5[:,0]),np.mean(ctr5[:,1]))
	logging.debug(f'proposedctr: {proposedctr}')
	
	# calc distance between each and all the points within the vehicle radius of the proposed center
	for pt in apts:
		pt['dctr'] = lbl.linelen(pt['ctr'], proposedctr)

	apts = sorted(apts,  key=lambda a: a['dctr'])

	vehiclethreshold = 50
	bpoint = 0
	means = []
	for pt in apts:
		if pt['dctr'] > vehiclethreshold:
			bpoint = pt['mean']
		means.append(pt['mean'])
	if bpoint == 0:
		bpoint = np.max(means)
		
	return bpoint

def calcDistances(ctrs):
	apts = []  # all point objects
	means = []

	# input is an array of centerpoints of the contours found in the mask
	# calculate the distance between each point and every other point
	# this results in an array for each point, containing the distances to all other points
	for ptA in ctrs:
		distances = []
		for ptB in ctrs:
			lenAB = lbl.linelen(ptA,ptB)
			distances.append(lenAB)

		# take the mean of all distances for this point
		mean = np.mean(distances)
		means.append(mean)

		# save the array and mean distance for each point
		#pt = {'ctr':ptA, 'distances':distances, 'mean':mean}
		pt = {'ctr':ptA, 'mean':mean}
		apts.append(pt)	


	# if the means for all points are less than the vehicle size
	# that indicates there is only the one object, the vehicle 
	# all points are qualified
	bpoint = 0
	vehiclesizethreshold = 50
	if np.max(means) < vehiclesizethreshold:
		print(f'calcDistances: no outliers')
		bpoint = np.max(means)	
	else:
		# if some points have larger means
		# there must be additional objects and outlier points
		# these outliers will increase the means for all points
		# find the first point with a big jump in mean distances
		bpoint = findBreakPct(apts) 
		#bpoint = findSequenceBreaks(means)

		# logically the bpoint must be within the range of means values
		# if it's above or below, then it's not really a bpoint
		if bpoint <= np.min(means) or bpoint > np.max(means):
			breakpoint()	

	# take only the points that come befoe this big jump
	# the other points are considered too outliers
	qctrs = []  # qualified centerpoints
	dctrs = []  # disqualified centerpoints
	for pt in apts:
		if pt['mean'] < bpoint:
			qctrs.append(pt['ctr'])
		else:
			dctrs.append(pt['ctr'])

	logging.debug(f'calcDistances num input pts:{len(ctrs)}, num output ctrs:{len(qctrs)}')

	# we must take at least some
	if len(qctrs) <= 0:
		breakpoint()
	
	return [qctrs, dctrs, means]
	
		

# an object detection algorithm
# choose contours that are within proximity of one another
# then make one new contour via convexHull of the centerpoints
# alternative: use all the points of the chosen contours, not just the centers
def clustering(mask, cls, dim, maxcount, t):  
	ctrs = []
	sizes = []
	polygon = []
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		ctr = rect[0]
		size = rect[1]
		mean = np.mean(size)
		ctr = np.intp(ctr)
		#if size > (5,5) and size < (100,100):
		ctrs.append(ctr)
		sizes.append(size)
	
	# qualify points based on distances from other points
	[qpts,dpts,means] = calcDistances(ctrs)

	# make convex hull out of qualified points
	qpts = np.array(qpts)
	hull = cv2.convexHull(qpts)

	# find rotated rect and make label of convex hull
	rect = cv2.minAreaRect(hull) 
	rmse = scr.calcRMSE(dim, rect[1])
	label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
	logging.debug(f'clustered label:{label}')
	return [label],[qpts,dpts,means] 

# an object detection algorithm
def labelsFromMask(mask, cls, dim, maxcount):  # with size closest to expected dimensions 
	labels = []
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	armse = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		size = rect[1]
		rmse = scr.calcRMSE(dim, size)
		armse.append(rmse)
		label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
		labels.append(label)

	# sort the labels ascending by error
	sortedlabels = sorted(labels, key=lambda a: a[lbl.scr])

	# take the n with lowest score
	bestlabels = sortedlabels[0:maxcount]

	# convert error to probability
	maxerror = max(armse)
	for label in bestlabels:
		rmse = label[lbl.scr]
		prob = scr.calcProbability(rmse, maxerror)
		label[lbl.scr] = prob
	return bestlabels

# an object detection algorithm
def preprocessMask(mask):
	kernelsize = 3
	dilateiterations = 3
	kernel = np.ones((kernelsize, kernelsize))
	#mask = cv2.dilate(mask, kernel, iterations=dilateiterations)
	#mask = cv2.erode(mask, kernel, iterations=dilateiterations)
	return mask

def detectRunningDiff(fnum, frame, previousframe):
	global gfnum
	gfnum = fnum  # temp for use in calcSequenceBreaks
	cls = 2  # fix this

	# diff from previous frame
	diff = diffFrames(frame, previousframe)

	# make mask via otsu threshold
	gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
	t, mask = cv2.threshold(gray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	
	# if otsu t value is too low, it means there's no diff, no movement
	diffThreshold = 5
	if t < diffThreshold:
		logging.debug(f'low t {t}, no movement')
		return [[cls,0,0,0,0,0,0]], [diff, gray, mask, [[],[],[]] ]

	# preprocess mask
	labels, cluster = clustering(mask, cls, (50,70), 1, t)
	
	return labels, [diff, gray, mask, cluster]

def processFrame(frame, fnum, previousframe):
	return detectRunningDiff(fnum, frame, previousframe)

# main loop thru all frames, cam vs awacs
def looper():
	previousframe,_ = getFrame(1)
	framecnt = 0
	increment = 1

	# debugging
	labelsets = []
	frames = []
	diffs = []
	grays = []
	masks = []
	aframes = []
	clusters = []

	while True:
		frame,fnum = getFrame(increment)
		if frame is None:
			break;
		framecnt += 1
		logging.info(f'frame:{framecnt}, fnum:{fnum}')

		labels, [diff, gray, mask, cluster] = processFrame(frame, fnum, previousframe)

		# debugging: change title when labels indicates no movement
		title = fnum
		if labels[0][lbl.scr] == 0:
			title = f'{fnum} no movement'

		# annotate labels on top of frame
		aframe = draw.drawImage(frame,labels,options={"title":title})

		# debug: draw points from clustering
		[qpts, dpts, means] = cluster
		for qpt in qpts:
			aframe = cv2.circle(aframe, qpt, 2, (0,255,0), -1)
		for dpt in dpts:
			aframe = cv2.circle(aframe, dpt, 2, (0,0,255), -1)

		# debugging
		labelsets.append(labels)
		frames.append(frame)
		diffs.append(diff)
		grays.append(gray)
		masks.append(mask)
		clusters.append(cluster)
		aframes.append(aframe)

		if gargs.olabelsufx:
			lbl.write(labels,frm.fqjoin(gargs.idir, fnum, gargs.olabelsufx))


		if gargs.nthshow > 0 and (framecnt % gargs.nthshow) == 0:
			# debugging choice of images to show
			#imagearray = diffs+masks+aframes
			#columncount = len(diffs)
			imagearray = aframes
			columncount = 6

			# debugging reset arrays
			labelsets = []
			frames = []
			diffs = []
			gray = []
			masks = []
			clusters = []
			aframes = []

			waiting = True
			while waiting:
				key = draw.showImage(imagearray, fps=gargs.fps, cols=columncount)
				if key == ord('q'):
					waiting = False
				elif key == ord('n'):
					increment = 1   # n next
					waiting = False
				elif key == ord('p'):
					increment = -1  # p previous
					waiting = False

			if key == ord('q'):        # q quit
				break
		previousframe = frame

	cv2.destroyAllWindows()


def getOptions():
	defidir = 'photos/20231216-092941/'  # day
	defiext = 'jpg'
	defnthshow = 0
	deffps = 0
	defolabelsufx = 'label.csv'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'                           ,default=defidir      ,help='input folder'        )
	parser.add_argument('-ie' ,'--iext'                           ,default=defiext      ,help='input extension'     )
	parser.add_argument('-ns' ,'--nthshow'   ,type=int            ,default=defnthshow   ,help='stop and refresh UI every nth frame'   )
	parser.add_argument('-fps','--fps'       ,type=int            ,default=deffps       ,help='fps, when nthshow is 0'   )
	parser.add_argument('-ol' ,'--olabelsufx'                     ,default=defolabelsufx,help='suffix of output label file'   )
	parser.add_argument('-v'  ,'--verbose'   ,action='store_true' ,default=False   ,help='display additional output messages'    ),
	parser.add_argument('-q'  ,'--quiet'     ,action='store_true' ,default=False   ,help='suppresses all output'                 ),
	parser.add_argument('-m'  ,'--manual'    ,action='store_true' ,default=False   ,help='let user initialize the model manually'),
	args = parser.parse_args()	# returns Namespace object, use dot-notation
	return args

def setupLogging(verbose,quiet):
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if gargs.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if gargs.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(gargs)

# setup, then launch looper()
def main():
	global gargs
	gargs = getOptions()
	setupLogging(gargs.verbose, gargs.quiet)
	looper()

if __name__ == "__main__":
	main()

