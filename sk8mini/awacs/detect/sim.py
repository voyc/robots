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
import model as mod


# global constants for rdiff algorithm - add these as specs in the model so they can be tweaked with trackbars
gthresholdDiffT     =   5  # runningDiff, otsu T value, below which the mask is assumed to blank, meaning there's no difference
gthresholdPctMean   =   5  # runningDiff, pct increase in mean distance, below which are assumed to be an object
gthresholdSk8Radius = 100  # runningDiff, radius of Sk8

# global variables
gargs = None     # fixed constants set at startup
gmodel = []      # read from disk
gframendx = -1   # used by getFnum() only
gframelist = []  # used by getFnum() only
gfnum = ''       # debugging info, for titles and logging

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
	fnum = gframelist[gframendx]
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
	print('readTrackbars')
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
	global gframes
	cls = modcls['cls']

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
		rmse = scr.calcRMSE(modcls['dim'], rect[1])
		label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
		logging.debug(f'clustered label:{label}')

	cover = makeClusteredOverlay(frame, qctrs, dctrs, proctr, hull)
	if (cls == gargs.clsshow):
		frm.cache('cover', cover)
	return [label]

def detectColor(modcls, frame):
	global gframes
	#"values": [0, 69, 108, 156, 77, 148, 14, 40, 15, 40],  #night
        #"values": [ 27, 76, 119, 255, 101, 196, 11, 27, 11, 27], #day

	[cn,cx,sn,sx,vn,vx,wn,wx,hn,hx] = modcls['values']
	lower = np.array([cn,sn,vn])
	upper = np.array([cx,sx,vx])
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	mask = cv2.inRange(hsv,lower,upper)
	if (modcls['cls'] == gargs.clsshow):
		frm.cache('mask', mask)

	mask = preprocessMask(mask)
	labels = labelsFromMask(mask, modcls['cls'], modcls['dim'], modcls['count'])

	return labels

def detectGray(modcls, frame):
	global gframes
	#"values": [0, 69, 108, 156, 77, 148, 14, 40, 15, 40],  #night
        #"values": [ 27, 76, 119, 255, 101, 196, 11, 27, 11, 27], #day

	[gn,gx,wn,wx,hn,hx] = modcls['values']
	lower = np.array([cn,sn,vn])
	upper = np.array([cx,sx,vx])
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
	mask = cv2.inRange(hsv,lower,upper)
	if (cls == gargs.clsshow):
		frm.cache('mask', mask)

	mask = preprocessMask(mask)
	labels = labelsFromMask(mask, modcls['cls'], modcls['dim'], modcls['count'])

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
	print('processFrame')

	modcls = mod.getModcls(model,cls)

	if gargs.clstweak and gargs.clstweak == modcls['cls']:
		if gtweakopen:
			if gguievent != GUI_EVENT_NONE:
				values = processGuiEvent(gguievent)
				print(f'values:{values}')
				modcls['values'] = values
				gguievent = GUI_EVENT_NONE
		else:
			openTweak(modcls)
			gtweakopen = True

	'''
	0_model.mson

	1 cone algo=color
	2 sk8  algo=rdiff
	3 donut2 algo=1
	4 donut3 algo=1
	5 donut4 algo=1
	6 led    algo=1 led
	7 wheel algo=wheel
	8 deck   algo=3

	9 wheelbase algo=wheelbase
	10 sk8box  algo=sk8box
	23 disqualified wheels, rejected by clustering algorithm

	[1,2,7]

	'''



	if modcls['algo'] == 'color':
		labels = detectColor(modcls, frame)
	elif modcls['algo'] == 'rdiff':
		labels = detectRunningDiff(modcls, frame, previousframe)
	elif modcls['algo'] == 'wheel':
		labels = detectWheels(modcls, frame, previousframe, labels)
	logging.info(f'labels: {labels}')
	return labels

# main loop thru all frames, cam vs awacs
def looper():
	global gframes, gguievent
	previousframe = getFrame(1)   # set previousframe and then in process...() set the first frame to no labels
	framecnt = 0
	increment = 1

	colortable = makeColorTable()

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
		title = f'{gfnum} no movement'
		aframe = draw.drawImage(frame,labels,options={"title":title, "colors":colortable})
		frm.cache('aframe', aframe)

		if gargs.olabelsufx:
			lbl.write(labels,frm.fqjoin(gargs.idir, gfnum, gargs.olabelsufx))

		# show the output, keyboard navigation, mouse and trackbar events
		if gargs.nthshow > 0 and (framecnt % gargs.nthshow) == 0:
			imagearray = []
			for name in gargs.dnames:
				imagearray += frm.getCached(name)
			frm.clearCache() # reset for next set

			waiting = True
			while waiting:
				cols, rows = gargs.grid
				img = draw.stack(imagearray, cols=cols, rows=rows, screen=gargs.screen)
				cv2.imshow( 'show', img)
				key = cv2.waitKey(1)
				if key == ord('q'):
					waiting = False
				elif key == ord('n') or gargs.fps > 0:
					increment = 1   # n next
					waiting = False
				elif key == ord('p'):
					increment = -(gargs.nthshow*2)+1  # p previous
					waiting = False

				elif gguievent != GUI_EVENT_NONE or key == ord('t'):
					increment = -gargs.nthshow+1  # t tweak
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
	defgrid = '1x1'
	defscreen = '1910x900'
	defolabelsufx = ''   # 'label.csv'
	defimodel = 'model'
	defdnames = 'aframe'

	defclsrun = [1,2,7]
	defclsshow = 1
	defclstweak = 1
	defframedebug = ''

	# get command-line parameters 
	# file inputs
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'                           ,default=defidir      ,help='input folder'        )
	parser.add_argument('-ie' ,'--iext'                           ,default=defiext      ,help='input extension'     )
	parser.add_argument('-m'  ,'--imodel'                         ,default=defimodel,    help='input model file'),

	# file outputs
	parser.add_argument('-ol' ,'--olabelsufx'                     ,default=defolabelsufx,help='suffix of output label file'   )

	# onscreen display options
	parser.add_argument('-ns' ,'--nthshow'   ,type=int            ,default=defnthshow   ,help='stop and refresh UI every nth frame'   )
	parser.add_argument('-fps','--fps'       ,type=int            ,default=deffps       ,help='fps, when nthshow is 0'   )
	parser.add_argument('-g'  ,'--grid'      ,nargs=2  ,type=int  ,default=defgrid      ,help='display grid as cols,rows'   )
	parser.add_argument('-scr','--screen'    ,nargs=2  ,type=int  ,default=defscreen    ,help='screen size as wid,ht'   )
	parser.add_argument('-dn' ,'--dnames'    ,nargs='*'           ,default=defdnames    ,help='list of display names'   )

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
	if args.nthshow == 0:
		logging.info('--nthshow is 0.  No display.')

	else:
		wd,ht = args.screen
		cols,rows = args.grid
		if not (cols * rows == args.nthshow * len(args.dnames)):
			logging.info('Display dimensions are inconsistent. Check grid, nthshow, dnames.')
			return False
	return True

def setupLogging(debug,quiet):
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if gargs.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if gargs.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(gargs)

# setup, then launch looper()
def main():
	global gargs,gmodel
	gargs = getOptions()

	setupLogging(gargs.verbose, gargs.quiet)

	ok = checkOptions(gargs)
	if not ok:
		return

	gmodel = mod.read(frm.fqjoin(gargs.idir, gargs.imodel, 'json'))
	looper()




'''

new shit

debugging cover:
	qualified wheels: rect
	disqualified wheels: rect
	wheel center: circle
	wheel contour: polygon
	crop box: square
	led: circle
	rect+arrow

prod cover:
	sk8 center
	sk8 arrow

truth labels: remove all cls's except cone and sk8



argparse nargs='*'
output=frame,mask,cover,aframe,amask,cmask
nthshow=6
grid=3x6

cols = number of output arguments
rows = nthshow

output defaults to aframe, count 1

if num output is 1,2,3
it is possible to have 2 or 3 rows

ie, specify grid as --grid=10x2 --output=frame,mask,cover --shownth=10

nthshow is number of frames
num(output) is number of images to show for each frame, always columnar vstack
grid is (cols,rows)
therefore
nthshow*noutputs = cols*rows 
default
cols = nthshow
rows = noutputs

example: --nthshow=1 --noutput=3 => --grid=1,3
example: --nthshow=6 --noutput=3 => --grid=6,3
example: --nthshow=6 --noutput=3 --grid=6,6 => grid has been overridden, 2 rows of frames

ocrop' in the output name means it has to be resized
'over' in the output name means it has transparent alpha channel
aframe has already been overlaid
map has already been overlaid on white background

output
production options: frame, map, aframe
debugging options: cmask, smask, dmask, cover,...

'''
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
	wdn,wdx,htn,htx, distance,nwn,nwx = values
	sizerange = np.array([wdn,wdx, htn, htx])
	numwheelsrange = np.array([nwn,nwx])

	# work with grayscale
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

	# make mask via gray range
	lower = 0
	gavg = np.mean(gray)
	upper = (.191 * gavg + 11.2) # see google sheets "Wheels Regression Line" for this equation
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
		print(f'further qualification is required {len(clusternums)}')
	if len(clusternums) <= 0:
		print('no qualified clusters')
		clusternum = 0
	else:
		clusternum = clusternums[0]
	clusteredlabels = []
	for labeldict in labeldicts:
		if labeldict['cluster'] == clusternum:
			clusteredlabels.append(labeldict['label'])
		else:
			labeldict['label'][lbl.cls] = 12  # highest cls in colorstack
			clusteredlabels.append(labeldict['label'])

	return clusteredlabels


def detectLed(modcls, frame, ilabels):
	#detectByHsv()
	#get sk8 label
	#qualify led, with shortest distance to a side 
	#which side?  (a,b,c,d)
	#adjust angle, with this side as the stern 
	
	olabels = []#  adjust sk8 label and merge led labels with input labels
	return olabels

def detectDeck(modcls, frame, ilabels):
#	olabels = detectWheels(modcls, frame, ilabels):
#	combine
#	rect
#	center
#	crop
#	detectLed(modcls, crop, ilabels) 
#	
	return olabels

def makeColorTable():
	colortable = []
	for ncolor in range(0,30):
		colortable.append('red')
	for modcls in gmodel:
		colortable[modcls['cls']] = modcls['acolor']
	return colortable


if __name__ == "__main__":
	main()

