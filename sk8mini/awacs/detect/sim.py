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
		write labelset to disk
		manual frame navigation
			pause, forward, back, speedup, slowdown
			show nth frames

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


#global constants - can be tweaked with trackbars
gthresholdDiffT     =   5  # runningDiff, otsu T value, below which the mask is assumed to blank, meaning there's no difference
gthresholdPctMean   =   5  # runningDiff, pct increase in mean distance, below which are assumed to be an object
gthresholdSk8Radius = 100  # runningDiff, radius of Sk8

gmodel = {
	'clsid':2,
	'algo':'rdiff',
	'dim':(50,70)
}
	
# global variables
gargs = None     # fixed constants set at startup
gframendx = -1   # used by getFnum() only
gframelist = []  # used by getFnum() only
gfnum = ''       # debugging info, for titles and logging
gdebugframes = [] # a list of intermediate frames, saved for here for debugging display

def getFnum(increment, loop=False):
	global gframendx, gframelist, gfnum
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
	gfnum = fnum
	return fnum

# camera simulation
def getFrame(increment):
	fnum = getFnum(increment)
	if not fnum:
		return None
	fnum = gframelist[gframendx]
	frame = cv2.imread(frm.fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
	return frame

def diffFrames(current,previous):
	imgDiff1 = cv2.absdiff(current, previous)	
	imgDiff2 = cv2.absdiff(current, imgDiff1)
	imgDiff3 = cv2.absdiff(previous, imgDiff2)
	return imgDiff3

# for debugging
def printObjectArray(objarray):
	for obj in objarray:
		logging.debug(obj)
	
def findProposedCenter(cntds, threshold):
  	# input list of dicts 
	# {'ctr':ctr, 'meandistance':mean, 'cnt':cnt, 'qualified':False}

	# sort by meandistance
	cntds = sorted(cntds,  key=lambda a: a['meandistance'])

	# calc pct increase in meandistance from one point to the next
	homepts = []
	prevmean = cntds[0]['meandistance']
	pct = 1
	for cntd in cntds:
		if prevmean > 0:
			pct = ((cntd['meandistance'] - prevmean) / prevmean) * 100 
			pct = max(pct,1)
		prevmean = cntd['meandistance']

		# save centerpoints within the meandistance threshold
		if pct < threshold:
			homepts.append(cntd['ctr'])
	
	# find center of homepts
	homepts = np.array(homepts)
	proposedcenter = (np.mean(homepts[:,0]),np.mean(homepts[:,1]))
	logging.debug(f'proposedcenter: {proposedcenter}')

	return proposedcenter 

# calculate the distance between each point and every other point 
# save the mean distance for each point, return the largest
def calcMeanDistance(cntds):
	means = []
	for cntd in cntds:
		distances = []
		ptA = cntd['ctr']
		for cntd2 in cntds:	
			ptB = cntd2['ctr']
			lenAB = lbl.linelen(ptA,ptB)
			distances.append(lenAB)
		# save the mean of these distances
		mean = np.mean(distances)
		cntd['meandistance'] = mean  # input array is updated
		means.append(mean)
	return np.max(means) # return largest

# given input list of contour descriptors, based on mutual proximity,
# find the likely center of our object and disqualify outlier points
def qualifyByProximity(cntds, proctr, threshold):
	qctrs = []
	dctrs = []
	for cntd in cntds:
		lenpro = lbl.linelen(cntd['ctr'], proctr)
		logging.debug(f'qualifyByProximity distance from center: {lenpro}')
		if threshold <= 0 or lenpro < threshold:
			cntd['qualified'] = True
			qctrs.append(cntd['ctr'])
		else:
			dctrs.append(cntd['ctr'])
	return qctrs, dctrs

# return a convex hull enclosing all of the qualified contours
def combineContours(cntds):
	polygon = []
	for cntd in cntds:
		if cntd['qualified'] == True:
			for pt in cntd['cnt']:
				polygon.append(pt[0])
	polygon = np.array(polygon)
	hull = None
	if len(polygon) > 0:
		hull = cv2.convexHull(polygon)
	return hull

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

# object detection by comparing current frame to previous frame, output labels
def detectRunningDiff(model, frame, previousframe, cls):
	# diff current and previous frames
	diff = diffFrames(frame, previousframe)
	gdebugframes.append({'name':'diff', 'frame':diff})

	# convert to gray and make mask via otsu threshold
	gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
	t, mask = cv2.threshold(gray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	gdebugframes.append({'name':'gray', 'frame':gray})
	gdebugframes.append({'name':'mask', 'frame':mask})
	
	# if otsu t value is too low, it means there's no diff, no movement
	logging.info(f'diff otsu t:{t}')
	if t < gthresholdDiffT:
		logging.debug(f'low t {t}, no movement')
		return [lbl.nomovement]

	# find contours in the mask
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

	# make a list of contour descriptors, dicts describing and including each contour
	cntds = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		cntd = {'ctr':np.intp(rect[0]), 'size':rect[1], 'cnt':cnt, 'meandistance':0, 'qualified':False}
		cntds.append(cntd)

	# calculate mean distance for each contour center
	maxmean = calcMeanDistance(cntds)

	# if the means for all points are less than the vehicle size,
	# that indicates there is only the one object: the vehicle 
	# all points are qualified
	threshold = gthresholdSk8Radius
	if maxmean < threshold:
		threshold = 0
		logging.debug(f'detectRunningDiff: one center only, no outliers')

	# if some points have larger means
	# there must be additional objects and outlier points
	# these outliers will increase the means for all points
	proctr = findProposedCenter(cntds, gthresholdPctMean)
	qctrs, dctrs = qualifyByProximity(cntds, proctr, threshold) 
	hull = []
	if len(qctrs) <= 0:
		label = lbl.notfound
		logging.info(f'clustered object not found')
	else:
		# make convex hull out of qualified points
		#hull = cv2.convexHull(qpts)  # make hull from centers only
		hull = combineContours(cntds) # make hull from all points of the contour

		# find rotated rect and make label of convex hull
		rect = cv2.minAreaRect(hull) 
		rmse = scr.calcRMSE(model['dim'], rect[1])
		label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
		logging.debug(f'clustered label:{label}')

	cover = makeClusteredOverlay(frame, qctrs, dctrs, proctr, hull)
	gdebugframes.append({'name':'cover', 'frame':cover})
	return [label]

def makeClusteredOverlay(frame, qpts, dpts, proctr, hull):
	cover = draw.createImage(frame.shape, color=(0,0,0))
	if len(hull):
		cv2.drawContours(cover, [hull], -1, (255,0,0), 1)

	proctr = np.array(proctr, dtype='int_')
	cover = cv2.circle(cover, proctr, 4, (255,0,0), -1)
	for qpt in qpts:
		cover = cv2.circle(cover, qpt, 2, (0,255,0), -1)
	for dpt in dpts:
		cover = cv2.circle(cover, dpt, 2, (0,0,255), -1)
	return cover	

def processFrame(model, frame, previousframe):
	if model['algo'] == 'color':
		labels = detectColor(frame)
	elif model['algo'] == 'rdiff':
		labels = detectRunningDiff(model, frame, previousframe, model['clsid'])
	logging.info(labels)
	return labels

# main loop thru all frames, cam vs awacs
def looper():
	previousframe = getFrame(1)
	framecnt = 0
	increment = 1

	# debugging, save for groups of frames
	aframes = []

	while True:
		frame = getFrame(increment)
		if frame is None:
			break;
		framecnt += 1
		logging.info(f'frame:{framecnt}, fnum:{gfnum}')

		labels = processFrame(gmodel, frame, previousframe)
		#[diff, gray, mask, cluster] = gdebugframe

		# debugging: change title when labels indicates no movement
		title = gfnum
		if labels[0][lbl.scr] == 0:
			title = f'{gfnum} no movement'

		# annotate labels on top of frame
		aframe = draw.drawImage(frame,labels,options={"title":title})
		aframes.append(aframe)

		if gargs.olabelsufx:
			lbl.write(labels,frm.fqjoin(gargs.idir, gfnum, gargs.olabelsufx))

		cover = getDebugFrames('cover')[0]
		cv2.imwrite('cover.jpg', cover)

		if gargs.nthshow > 0 and (framecnt % gargs.nthshow) == 0:
			imagearray = aframes
			imagearray = aframes+getDebugFrames('mask')+getDebugFrames('cover')

			# debugging reset arrays
			aframes = []
			gdebugframes = []

			waiting = True
			while waiting:
				key = draw.showImage(imagearray, fps=gargs.fps, grid=gargs.grid, screen=gargs.screen)
				if key == ord('q'):
					waiting = False
				elif key == ord('n') or gargs.fps > 0:
					increment = 1   # n next
					waiting = False
				elif key == ord('p'):
					increment = -1  # p previous
					waiting = False

			if key == ord('q'):        # q quit
				break
		previousframe = frame

	cv2.destroyAllWindows()

def getDebugFrames(name):
	out = []
	for frm in gdebugframes:
		if frm['name'] == name:
			out.append(frm['frame'])
	return out

def getOptions():
	defidir = 'photos/20231216-092941/'  # day
	defiext = 'jpg'
	defnthshow = 0
	deffps = 0
	defgrid = '1x1'
	defscreen = '1910x900'
	defolabelsufx = 'label.csv'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'                           ,default=defidir      ,help='input folder'        )
	parser.add_argument('-ie' ,'--iext'                           ,default=defiext      ,help='input extension'     )
	parser.add_argument('-ns' ,'--nthshow'   ,type=int            ,default=defnthshow   ,help='stop and refresh UI every nth frame'   )
	parser.add_argument('-fps','--fps'       ,type=int            ,default=deffps       ,help='fps, when nthshow is 0'   )
	parser.add_argument('-g'  ,'--grid'                           ,default=defgrid      ,help='display grid as colsxrows'   )
	parser.add_argument('-scr','--screen'                         ,default=defscreen    ,help='screen size as widxht'   )
	parser.add_argument('-ol' ,'--olabelsufx'                     ,default=defolabelsufx,help='suffix of output label file'   )
	parser.add_argument('-d'  ,'--debug'     ,action='store_true' ,default=False   ,help='display additional logging'    ),
	parser.add_argument('-q'  ,'--quiet'     ,action='store_true' ,default=False   ,help='suppresses all output'                 ),
	parser.add_argument('-m'  ,'--manual'    ,action='store_true' ,default=False   ,help='let user initialize the model manually'),
	args = parser.parse_args()	# returns Namespace object, use dot-notation

	# split screen and grid
	wd,ht = args.screen.split('x')
	args.screen = np.array([wd,ht],dtype='int_')
	cols,rows = args.grid.split('x')
	args.grid = np.array([cols,rows],dtype='int_')
	return args

def setupLogging(debug,quiet):
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if gargs.debug:
		logging.getLogger('').setLevel(logging.DEBUG)
	if gargs.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(gargs)

# setup, then launch looper()
def main():
	global gargs
	gargs = getOptions()

	setupLogging(gargs.debug, gargs.quiet)
	looper()

if __name__ == "__main__":
	main()

