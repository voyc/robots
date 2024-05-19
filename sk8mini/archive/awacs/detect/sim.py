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
import model as mod


# global constants for rdiff algorithm - add these as specs in the model so they can be tweaked with trackbars
gthresholdDiffT     =   5  # runningDiff, otsu T value, below which the mask is assumed to blank, meaning there's no difference
gthresholdPctMean   =   5  # runningDiff, pct increase in mean distance, below which are assumed to be an object
gthresholdSk8Radius = 100  # runningDiff, radius of Sk8

# global variables
gargs = None     # fixed constants set at startup
ggrid = [1,1]    # calculate based on gargs
gmodel = []      # read from disk
gframendx = -1   # used by getFnum() only
gframelist = []  # used by getFnum() only
gfnum = ''       # for titles and logging
gclscolors = []  # from model
gclsids = []     # from model
gwarnings = []   # list frames with errors that prevent successful detection

# global variables for tweak window
gtweakname = ''     # named window for trackbars
gtweakspecs = []    # for use between onMouse and onTrackbar
gtweakvalues = []   # for use between onMouse and onTrackbar
gtweakopen = False

GUI_EVENT_NONE     = 0
GUI_EVENT_TRACKBAR = 1
GUI_EVENT_MOUSE    = 2
gguievent = GUI_EVENT_NONE

#---------------- frame functions -----------------------
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
	frame = cv2.imread(frm.fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
	return frame

#--------------- tweak window ---------------------------------# 

def donothing(a): # default trackbar callback
	pass

def onTrackbar(newvalue):
	global gguievent
	gguievent = GUI_EVENT_TRACKBAR

def onMouse(event, x, y, flags, param):
	global gguievent
	if event == cv2.EVENT_LBUTTONDOWN:
		gguievent = GUI_EVENT_MOUSE

def processGuiEvent( event):
	if event == GUI_EVENT_TRACKBAR:
		values = readTrackbars(gtweakname, gtweakspecs)

	elif event == GUI_EVENT_MOUSE:
		[b,g,r] = gimage[y,x]
		h,s,v = draw.HSVfromBGR(b,g,r)
		#print(f'({x},{y}) : ({b},{g},{r}) : ({h},{s},{v}) ')
		
		hr = 20
		sr = 50
		vr = 50
		hn = max(h - hr,0)
		hx = min(h + hr,180)
		sn = max(s - sr,0)
		sx = min(s + sr,255)
		vn = max(v - vr,0)
		vx = min(v + vr,255)
		values = np.intp([hn,hx,sn,sx,vn,vx])
		setTrackbars(gtweakname, gtweakspecs, values)
		values = readTrackbars(gtweakname, gtweakspecs)
	return values

def openTweak(modcls):
	global gtweakname, gtweakspecs, gtweakvalues

	windowname = f'{modcls["name"]} settings'
	cv2.namedWindow( windowname, cv2.WINDOW_NORMAL)
	cv2.resizeWindow(windowname, 500, 600) 
	cv2.moveWindow(windowname, 1400, 100) 

	spec = modcls['spec']
	values = modcls['values']
	for ndx in range(0,len(spec)):
		name = spec[ndx]['name']
		value = values[ndx]
		upper = spec[ndx]['upper']
		cv2.createTrackbar(name, windowname, value, upper, onTrackbar)
	cv2.setMouseCallback(windowname, onMouse)
	
	gtweakspecs = spec
	gtweakvalues = values
	gtweakname = windowname

def setTrackbars(windowname, specs, values):
	for n in range(0,len(specs)):
		cv2.setTrackbarPos(specs[n]['name'], windowname, values[n])

def readTrackbars(windowname, specs):
	values = []
	for spec in specs:
		value = cv2.getTrackbarPos(spec['name'], windowname)
		values.append( value)
	return values

#--------------- inner loop per cls ------------------------------------# 

def diffFrames(current,previous):
	imgDiff1 = cv2.absdiff(current, previous)	
	imgDiff2 = cv2.absdiff(current, imgDiff1)
	imgDiff3 = cv2.absdiff(previous, imgDiff2)
	return imgDiff3

# for debugging
def logObjectArray(objarray):
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
	if maxcount > 0:
		bestlabels = sortedlabels[0:maxcount]
	else:
		bestlabels = sortedlabels

	# convert error to probability
	#maxerror = max(armse)
	maxerror = 2 * dim[0] * dim[1]

	for label in bestlabels:
		rmse = label[lbl.scr]
		prob = scr.calcProbability(rmse, maxerror)
		label[lbl.scr] = prob
	return bestlabels

# an object detection algorithm
def labelsFromContours(cnts, cls):
	labels = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		label = lbl.labelFromRect(cls, rect, which=False, score=0)
		labels.append(label)
	return labels

# an object detection algorithm
def preprocessMask(mask):
	kernelsize = 3
	dilateiterations = 3
	kernel = np.ones((kernelsize, kernelsize))
	#mask = cv2.dilate(mask, kernel, iterations=dilateiterations)
	#mask = cv2.erode(mask, kernel, iterations=dilateiterations)
	return mask

# object detection by comparing current frame to previous frame, output labels
def detectRunningDiff(modcls, frame, previousframe):
	cls = modcls['cls']

	if previousframe is None:
		return [lbl.nomovement(cls)]

	# diff current and previous frames
	diff = diffFrames(frame, previousframe)
	if (cls == gargs.clsshow):
		frm.cache('diff', diff)

	# convert to gray and make mask via otsu threshold
	gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
	t, mask = cv2.threshold(gray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	if (cls == gargs.clsshow):
		frm.cache('gray', gray)
		frm.cache('mask', mask)
	
	# if otsu t value is too low, it means there's no diff, no movement
	logging.info(f'diff otsu t:{t}')
	if t < gthresholdDiffT:
		logging.debug(f'low t {t}, no movement')
		if (cls == gargs.clsshow):
			frm.cache('cover', draw.createMask(frame.shape))
		return [lbl.nomovement(cls)]

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
		label = lbl.notfound(cls)
		logging.info(f'clustered object not found')
	else:
		# make convex hull out of qualified points
		#hull = cv2.convexHull(qpts)  # make hull from centers only
		hull = combineContours(cntds) # make hull from all points of the contour

		# find rotated rect and make label of convex hull
		rect = cv2.minAreaRect(hull) 
		rmse = scr.calcRMSE(modcls['dim'], rect[1])
		label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
		logging.debug(f'clustered label:{label}')

	cover = makeClusteredOverlay(frame, qctrs, dctrs, proctr, hull)
	if (cls == gargs.clsshow):
		frm.cache('cover', cover)
	return [label]

def detectColor(modcls, frame):
	#"values": [0, 69, 108, 156, 77, 148, 14, 40, 15, 40],  #night
        #"values": [ 27, 76, 119, 255, 101, 196, 11, 27, 11, 27], #day

	[cn,cx,sn,sx,vn,vx,wn,wx,hn,hx] = modcls['values']
	lower = np.array([cn,sn,vn])
	upper = np.array([cx,sx,vx])
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	h,s,v = cv2.split(hsv)

	avgh = np.mean(h)
	avgs = np.mean(s)
	avgv = np.mean(v)
	logging.info(f'{gfnum} h:{avgh} s:{avgs} v:{avgv}')

	mask = cv2.inRange(hsv,lower,upper)
	if (modcls['cls'] == gargs.clsshow):
		frm.cache('mask', mask)

	mask = preprocessMask(mask)
	labels = labelsFromMask(mask, modcls['cls'], modcls['dim'], modcls['count'])

	labels = qualifyLabelsBySize(labels, [wn,wx,hn,hx])
	return labels

def detectCone(modcls, frame):
	#"values": [0, 69, 108, 156, 77, 148, 14, 40, 15, 40],  #night
        #"values": [ 27, 76, 119, 255, 101, 196, 11, 27, 11, 27], #day

	[cn,cx,sn,sx,vn,vx,wn,wx,hn,hx] = modcls['values']

	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	h,s,v = cv2.split(hsv)
	avgh = np.mean(h)
	avgs = np.mean(s)
	avgv = np.mean(v)
	logging.info(f'{gfnum} h:{avgh} s:{avgs} v:{avgv}')

	# replace sat-lo with a function of avg sat
	w1 = -0.947
	w2 = 0.00982
	b = 141
	#sn = (w1 * avgs) + (w2 * (avgs**2)) + b
	#logging.info(f'sn: {sn} {int(sn)}')
	#sn = int(sn)

	lower = np.array([cn,sn,vn])
	upper = np.array([cx,sx,vx])

	mask = cv2.inRange(hsv,lower,upper)
	if (modcls['cls'] == gargs.clsshow):
		frm.cache('mask', mask)

	mask = preprocessMask(mask)
	labels = labelsFromMask(mask, modcls['cls'], modcls['dim'], modcls['count'])

	labels = qualifyLabelsBySize(labels, [wn,wx,hn,hx])
	return labels

def detectGray(modcls, frame):
	cls = modcls['cls']
	[gn,wn,wx,hn,hx] = modcls['values']
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	_, mask = cv2.threshold(gray, gn, 255, cv2.THRESH_BINARY)
	if (cls == gargs.clsshow):
		frm.cache('gray', gray)
		frm.cache('mask', mask)

	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	labels = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		label = lbl.labelFromRect(cls, rect, which=False, score=0)
		[c,x,y,w,h,a,p] = label
		if w>=wn and w<=wx and h>=hn and h<=hx:
			labels.append(label)

	return labels

#def detectDonut(modcls, frame):
#	# find range of gn where label count is 1
#	for gn in range:w




def detectDonut(modcls, frame):
	dimdonut = [25,25]
	dimdhole = [12,12]
	cls = modcls['cls']
	[gn,gx,wn,wx,hn,hx] = modcls['values']
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	#_, mask = cv2.threshold(gray, gn, 255, cv2.THRESH_BINARY)

	gx = gn + 12
	mask = cv2.inRange(gray, gn, gx)

	gavg = np.mean(gray)  # average gray is between 62 and 126, depending on the light
	logging.info(f'fnum {gfnum} gavg {gavg}')


	if (cls == gargs.clsshow):
		frm.cache('gray', gray)
		frm.cache('mask', mask)

	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	labels = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		label = lbl.labelFromRect(cls, rect, which=False, score=0)
		[c,x,y,w,h,a,p] = label
		if w>=wn and w<=wx and h>=hn and h<=hx:
			labels.append(label)

	return labels

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

def processFrame(model, cls, frame, previousframe, labels):
	global gmodel, gtweakopen, gguievent
	modcls = mod.getModcls(model,cls)
	if gargs.clstweak and gargs.clstweak == modcls['cls']:
		if gtweakopen:
			if gguievent != GUI_EVENT_NONE:
				values = processGuiEvent(gguievent)
				modcls['values'] = values
				gguievent = GUI_EVENT_NONE
		else:
			openTweak(modcls)
			gtweakopen = True

	olabels = []
	if modcls['algo'] == 'color':
		olabels = detectColor(modcls, frame)
	elif modcls['algo'] == 'cone':
		olabels = detectCone(modcls, frame)
	elif modcls['algo'] == 'donut':
		olabels = detectDonut(modcls, frame)
	elif modcls['algo'] == 'gray':
		olabels = detectGray(modcls, frame)
	elif modcls['algo'] == 'rdiff':
		olabels = detectRunningDiff(modcls, frame, previousframe)
	elif modcls['algo'] == 'wheel':
		olabels = detectWheels(modcls, frame, previousframe, labels)
	elif modcls['algo'] == 'led':
		olabels = detectLed(modcls, frame, previousframe, labels)
	logging.debug(f'olabels: {olabels}')
	return olabels

# main loop thru all frames, cam vs awacs
def looper():
	global gguievent
	#previousframe = getFrame(1)   # set previousframe and then in process...() set the first frame to no labels
	previousframe = None
	framecnt = 0
	increment = 1

	while True:
		frame = getFrame(increment)
		if frame is None:
			break;
		increment = 1
		framecnt += 1
		logging.info(f'frame:{framecnt}, fnum:{gfnum}')
		frm.cache('frame', frame)
	
		# process all frames, one cls at a time in this order, concatenate labels
		if gargs.framedebug and gargs.framedebug == gfnum:
			breakpoint()
		labels = []
		for cls in gargs.clsrun:
			labels += processFrame(gmodel, cls, frame, previousframe, labels)
	
		# annotate labels on top of frame
		title = f'{gfnum}'
		aframe = draw.annotateImage(frame,labels,gmodel,options={"title":title}, selected=-1)
		frm.cache('aframe', aframe)

		if gargs.olabelsufx:
			lbl.write(labels,frm.fqjoin(gargs.olabeldir, gfnum, gargs.olabelsufx))

		# show the output, keyboard navigation, mouse and trackbar events
		if gargs.nthshow > 0 and (framecnt % gargs.nthshow) == 0:
			imagearray = []
			for name in gargs.workframes:
				iarray = frm.getCached(name)
				imagearray += iarray
				if len(iarray) < gargs.nthshow:
					warn(f'{gfnum}: too few cached images for {name}: {len(iarray)}')
			frm.clearCache() # reset for next set

			waiting = True
			while waiting:
				img = draw.stack(imagearray, grid=ggrid, screen=gargs.screen)
				cv2.imshow( 'show', img)
				key = cv2.waitKey(1)
				if key == ord('q'):
					waiting = False
				elif key == ord('n') or gargs.fps > 0:    # n next
					increment = 1                     
					waiting = False
				elif key == ord('p'):                     # p previous
					increment = -(gargs.nthshow*2)+1
					waiting = False
				elif key == ord('w'):                     # w write model
					mod.write(gmodel,frm.fqjoin(gargs.idir, gargs.imodel, 'json'))
					waiting = False

				elif gguievent != GUI_EVENT_NONE or key == ord('t'):
					increment = -gargs.nthshow+1  # t tweak
					waiting = False

			if key == ord('q'):        # q quit
				break
		previousframe = frame

	cv2.destroyAllWindows()

def getOptions():
	defidir = 'photos/training/'
	defolabeldir= 'photos/training/labels/'
	defiext = 'jpg'
	defnthshow = 0
	deffps = 0
	defscreen = [1910,900]
	defolabelsufx = 'gtruth.txt'
	defimodel = '0_model'
	defworkframes = ['aframe']
	defclsrun = [1,2,3,7]
	defclsshow = 3
	defclstweak = 3
	defframedebug = ''

	# get command-line parameters 
	# file inputs
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'                           ,default=defidir      ,help='input folder'        )
	parser.add_argument('-ie' ,'--iext'                           ,default=defiext      ,help='input extension'     )
	parser.add_argument('-m'  ,'--imodel'                         ,default=defimodel,    help='input model file'),

	# file outputs
	parser.add_argument('-od' ,'--olabeldir'                      ,default=defolabeldir ,help='output folder for labels'   )
	parser.add_argument('-ol' ,'--olabelsufx'                     ,default=defolabelsufx,help='suffix of output label file'   )

	# onscreen display options
	parser.add_argument('-ns' ,'--nthshow'   ,type=int            ,default=defnthshow   ,help='stop and refresh UI every nth frame'   )
	parser.add_argument('-fps','--fps'       ,type=int            ,default=deffps       ,help='fps, when nthshow is 0'   )
	parser.add_argument('-scr','--screen'    ,nargs=2  ,type=int  ,default=defscreen    ,help='screen size as wid,ht'   )
	parser.add_argument('-dn' ,'--workframes',nargs='*'           ,default=defworkframes,help='list of working frames to display'   )

	# logging options
	parser.add_argument('-v'  ,'--verbose'   ,action='store_true' ,default=False   ,help='display additional logging'    ),
	parser.add_argument('-q'  ,'--quiet'     ,action='store_true' ,default=False   ,help='suppresses all output'                 ),

	# processing options
	parser.add_argument('-ct' ,'--clstweak'  ,type=int            ,default=defclstweak  ,help='which cls to tweak model'          ),
	parser.add_argument('-cr' ,'--clsrun'    ,nargs='*',type=int  ,default=defclsrun    ,help='which classes to run'   )
	parser.add_argument('-cs' ,'--clsshow'   ,type=int            ,default=defclsshow   ,help='which classes to display'   )
	parser.add_argument('-fd' ,'--framedebug'                     ,default=defframedebug,help='input model file'),
	args = parser.parse_args()	# returns Namespace object, use dot-notation

	return args

def checkOptions(args):
	global ggrid
	numframes = args.nthshow
	screendim = args.screen
	numworkframes = len(args.workframes)
	ggrid = calcGrid(numframes, screendim, numworkframes)
	return True

def calcGrid(numframes, screendim, numworkframes):
	arscreen = 0.0
	if numframes == 0:
		logging.info('--nthshow is 0.  No display.')
		grid = [0,0]
	elif numframes == 1:
		logging.debug('--nthshow is 1.  Working frames go horizontal.')
		grid = [numworkframes, numframes]
	elif numframes > 1 and numworkframes > 1:
		logging.debug('--nthshow > 1.  Working frames go vertical.')
		grid = [numframes, numworkframes]
	elif numframes > 1 and numworkframes == 1:
		logging.debug('--nthshow > 1.  One working frame.  1x1 grid recalculated.')
		wd,ht = screendim
		arscreen = wd/ht  # aspect ratio of the screen

		# find number of columns that best maintains the screen aspect ratio
		lowdiff = numframes
		lowcols = 0
		lowrows = 0
		for nrows in range(1, numframes+1):
			ncols = int(numframes / nrows)
			rem = numframes % nrows
			if rem > 0:
				ncols += 1
			argrid = ncols / nrows
			ardiff = abs(arscreen - argrid)
			diff = rem + ardiff
			if ardiff < lowdiff:
				lowdiff = ardiff
				lowcols = ncols
				lowrows = nrows
			logging.debug(f'{ncols},{nrows},{arscreen}, {argrid}, {ardiff},{rem}, {diff}')	
		#cols = lowcols
		#rows = lowrows  # rows = int(numframes / cols)
		grid = [lowcols,lowrows]
	return grid

def setupLogging(debug,quiet):
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if gargs.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if gargs.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(gargs)

def warn(msg):
	logging.warning(msg)
	gwarnings.append(msg)

# setup, then launch looper()
def main():
	global gargs,gmodel,gclsids
	gargs = getOptions()

	setupLogging(gargs.verbose, gargs.quiet)

	ok = checkOptions(gargs)
	if not ok:
		return

	gmodel = mod.read(frm.fqjoin(gargs.idir, gargs.imodel, 'json'))
	gclsids = makeClsidTable()

	looper()

	for msg in gwarnings:
		logging.warning(msg)

def qualifyLabelsBySize(labels, sizerange):
	wdn,wdx,htn,htx = sizerange
	lower = np.array((wdn,htn))
	upper = np.array((wdx,htx))
	qualified = []
	for label in labels:
		_,_,_,w,h,_,_ = label
		size = np.array((w,h))
		if all(size >= lower) and all(size <= upper):
			qualified.append(label)
	return qualified
	
def detectWheels(modcls, frame, previousframe, ilabels):
	# inputs
	cls = modcls['cls']
	values = modcls['values']
	weight, bias, wdn,wdx,htn,htx, distance,nwn,nwx = values
	sizerange = np.array([wdn,wdx, htn, htx])
	numwheelsrange = np.array([nwn,nwx])


	# work with grayscale
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	if (cls == gargs.clsshow):
		frm.cache('gray', gray)

	# make mask via gray range
	lower = 0
	#upper = (.191 * gavg + 11.2) # see google sheets "Wheels Regression Line" for this equation

	# detect black wheels based on lower values of gray
	gavg = np.mean(gray)  # average gray is between 62 and 126, depending on the light

	# upper needs to be lower for low light conditions, higher for high light conditions
	# we are using a linear equation to accomplish that
	# x = meangray gray
	# y = upper threshold

	weight /= 1000 # weight = .191,  trackbar 1:200, equation 0:0.200
	bias /= 10     # bias = 11.2,    trackbar 1:200, equation 0:20.0
	upper = (weight * gavg + bias) # see google sheets "Wheels Regression Line" for this equation
	mask = cv2.inRange(gray, lower, upper)

	if (cls == gargs.clsshow):
		frm.cache('mask', mask)

	# labels from mask, qualified by size
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	labels = labelsFromContours(cnts, cls)
	labels = qualifyLabelsBySize(labels, sizerange)

	# cluster wheel labels by distance, qualify by number
	labelsclustered = clusterLabels(labels, distance, numwheelsrange)

	# qualify wheel labels by number

	# cluster the centerpoints of the wheels
	# choose the cluster of the sk8
	# make tiny image as box around the centerpoint of the chosen cluster
	# within the tiny image
	# 	make a convex hull of the wheels
	# 	take rrect
	# 	find the led, adjust the heading of the sk8

	return labelsclustered

def clusterLabelsFixed(labels, dist, clusters):
	# input clusters is fixed array of points, one point per cluster 

	def assign(ctr,clusters,distance):
		lowdistance = 1000
		lowclusternum = -1
		for clusternum in range(0, len(clusters)):
			# check the distance of the input ctr to the centerpoint of each cluster
			ll = lbl.linelen(clusters[clusternum],ctr)
			if ll < distance and ll < lowdistance:
				lowdistance = ll
				lowclusternum = clusternum
		return lowclusternum

	# assign each label to a cluster
	labeldicts = []
	for label in labels:
		_,x,y,w,h,_,_ = label
		ctr = (x,y)
		clusternum = assign(ctr,clusters,dist)
		if clusternum >= 0:
			labeldict = {'ctr:':ctr, 'size':(w,h), 'label':label, 'cluster':clusternum}
			labeldicts.append(labeldict)

	# count the number of labels assigned to each cluster
	clustercounts = [0] * 4
	for labeldict in labeldicts:
		clustercounts[labeldict['cluster']] += 1

	# find cluster with the highest count of assigned leds
	hicount = 0
	hinum = -1
	for num in range(0, len(clustercounts)):
		if clustercounts[num] > hicount:
			hicount = clustercounts[num]
			hinum = num
	return hinum	

def clusterLabels(labels, dist, numwheelsrange):
	nwn, nwx = numwheelsrange

	def qualify(clusters, nwn, nwx):
		qualifiednums = []
		clusternum = 0
		for cluster in clusters:
			clusternum += 1
			if len(cluster) >= nwn and len(cluster) <= nwx: 
				qualifiednums.append(clusternum)
		return qualifiednums

	def assign(ctr,clusters,distance):
		clusternum = 1
		for cluster in clusters:
			# check the distance of the input pt to every point in the cluster
			inside = True 
			for pt in cluster:
				ll = lbl.linelen(pt,ctr)
				if ll > distance:
					inside = False
					break
			if inside == True:
				break 
			clusternum += 1
		if clusternum >= len(clusters):
			clusters.append([ctr])
		else:
			clusters[clusternum-1].append(ctr)
		return clusternum

	clusters = []  # clusterndx[0:len], clusternum[ndx+1]
	labeldicts = []
	for label in labels:
		_,x,y,w,h,_,_ = label
		ctr = (x,y)
		clusternum = assign(ctr,clusters,dist)
		labeldict = {'ctr:':ctr, 'size':(w,h), 'label':label, 'cluster':clusternum}
		labeldicts.append(labeldict)

	clusternums = qualify(clusters, nwn, nwx)
	if len(clusternums) > 1:
		logging.info(f'further qualification is required {len(clusternums)}')
	if len(clusternums) <= 0:
		logging.info('no qualified clusters')
		clusternum = 0
	else:
		clusternum = clusternums[0]
	clusteredlabels = []
	for labeldict in labeldicts:
		if labeldict['cluster'] == clusternum:
			clusteredlabels.append(labeldict['label'])
		else:
			# keep the label for debugging, change the clsid
			labeldict['label'][lbl.cls] = gclsids['dwheel']
			clusteredlabels.append(labeldict['label'])
	return clusteredlabels

def detectLed(modcls, frame, previousframe, ilabels):

	# inputs from model and trackbars
	radius, gv, wdn, wdx, htn, htx, dist = modcls['values']

	# pull "wheel" labels from the input label list, bail out if none
	pts = []
	for label in ilabels:
		cls, x,y,w,d,hdg,scr = label
		if cls == gclsids['wheel']:
			pts.append((x,y))
	if len(pts) <= 0:
		warn(f'{gfnum}: no wheels')
		if (modcls['cls'] == gargs.clsshow):
			frm.cache('crop', draw.createMask((200,200)))
			frm.cache('gray', draw.createMask((200,200)))
			frm.cache('mask', draw.createMask((200,200)))
		return []
	if len(pts) < 4:
		warn(f'{gfnum}: fewer than 4 wheels')

	# make the "wheelbase" label from the convex hull of the wheels
	pts = np.array(pts)
	hull = cv2.convexHull(pts)	
	(x,y), (w,h), a = cv2.minAreaRect(hull)
	wheelbaselabel = [int(item) for item in [gclsids['wheelbase'], x,y,w,h,a,0]]

	# make the "sk8box" label around the center of the wheelbase
	sizerange = wdn,wdx,htn,htx
	cls, x,y,w,d,hdg,scr = wheelbaselabel
	rect = ((x,y), (radius,radius), 0)	
	sk8boxlabel = lbl.labelFromRect(gclsids['sk8box'], rect, which=False, score=0)

	# crop the frame to the sk8box rectangle
	l = max(x - radius, 0)
	t = max(y - radius, 0)
	r = x + radius
	b = y + radius
	crop = frame[t:b,l:r]
	frm.cache('crop', crop)

	# find "led" labels within the cropped image
	gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
	gavg = np.mean(gray)
	#print(f'gavg:{gavg}, gv:{gv}')
	lower = gv 
	upper = 255
	# upper = (.191 * gavg + 11.2) # see google sheets "Wheels Regression Line" for this equation
	mask = cv2.inRange(gray, lower, upper)
	if (modcls['cls'] == gargs.clsshow):
		frm.cache('gray', gray)
		frm.cache('mask', mask)
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	ledlabels = labelsFromContours(cnts, modcls['cls'])
	ledlabels = qualifyLabelsBySize(ledlabels, sizerange)
	for label in ledlabels:
		label[lbl.cx] += l
		label[lbl.cy] += t

	# find the stern of the wheelbase rectangle as the side closest to the leds
	cls,x,y,w,h,hdg,scr = wheelbaselabel
	rect = ((x,y), (w,h), hdg)
	box = cv2.boxPoints(rect)
	box = np.intp(box)
	sidecenters = []
	for side in range(0,len(box)):
		sideb = side+1 if side+1 < len(box) else 0
		sidecenters.append( lineCenter(box[side], box[sideb]))
	sidestern = clusterLabelsFixed(ledlabels, dist, sidecenters) 

	# alter the hdg of the wheelbase label, now that we know the position of the stern
	if sidestern < 0:
		warn(f'{gfnum}: no qualified leds to identify stern')
		newhdg = -1
	else:
		newhdg = hdg + ((sidestern+1) * 90)
		if newhdg > 359: newhdg -= 360
	wheelbaselabel[lbl.hdg] = newhdg

	return [wheelbaselabel, sk8boxlabel] + ledlabels

def lineCenter(ptA, ptB):
	ptA = np.array(ptA)
	ptB = np.array(ptB)
	ctr = ptA + ((ptB - ptA) / 2)	
	return ctr

def makeClsidTable():
	clsidtable = {}
	for modcls in gmodel:
		clsidtable[modcls['name']] = modcls['cls']
	return clsidtable

if __name__ == "__main__":
	main()

