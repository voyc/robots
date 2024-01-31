'''
findsk8.py - find sk8, multiple hard-coded steps
'''
import cv2
import numpy as np
import os
import argparse
import copy

import detect 
import score 
import label as lbl
import draw
import model as modl

# global constants
gwindowname = 'find sk8'
gwindowsize = (1200, 900)

# global variables
gargs = None
gflag = False
gvalues = [0,50,0,50, 100, 0, 20, 40, 80, 50, 100] 
gvalues = [3,18,6,29,  71, 2, 10, 40, 80, 50, 100] 
gmodel = { 
	"cls": 7,
	"name": "wheel",
	"algo": "gray",
	"rotate": 1,
	"dim": [ 12, 16 ],
	"dimsk8": [ 50, 70 ],
	"count": 4
}
gsk8specs = [
	{ "name": "wd_min", "lower": 0, "upper": 100, },
	{ "name": "wd_max", "lower": 0, "upper": 100, },
	{ "name": "ht_min", "lower": 0, "upper": 100, },
	{ "name": "ht_max", "lower": 0, "upper": 100, },
	{ "name": "dist"  , "lower": 0, "upper": 200, },
	{ "name": "num_min", "lower": 0, "upper": 100, },
	{ "name": "num_max", "lower": 0, "upper": 100, },
]

#------------- add to draw.py  ------------------

def onTrackbarDefault(newvalue):
	pass

def onMouseDefault(event, x, y, flags, param):
	pass

def addTrackbars(windowname, specs, values, onTrackbar, onMouse):
	for n in range(0,len(specs)):
		name = specs[n]['name']
		upper = specs[n]['upper']
		value = values[n]
		cv2.createTrackbar(name, windowname, value, upper, onTrackbar)
	cv2.setMouseCallback(windowname, onMouse)

def setTrackbars(windowname, specs, values):
	for n in range(0,len(specs)):
		cv2.setTrackbarPos(specs[n]['name'], windowname, values[n])

def readTrackbars(windowname, specs):
	values = []
	for n in range(0,len(specs)):
		value = cv2.getTrackbarPos(specs[n]['name'], windowname)
		values.append(value)
	return values

#------------- add to draw.py  ------------------

def fqjoin(path, base, ext):
	if gargs.iext[0] != '.':
		gargs.iext = '.' + gargs.iext
	return os.path.join(path,base+ext)

#------------------------------------------------

'''
find wheels
find best cluster of wheels
make tiny square from center of best cluster
look for sk8 in tiny
	try hsv
	try gray
	try silt
	try cnn
find led in tiny
'''


def findSk8(full, values, cls):
	mask,labelswheels = findWheels(full, values, 3)
	labelsclustered = clusterLabels(labelswheels, values)
#	labelsk8 = combineLabelCenters(labels)
	#center from labelsk8

	#labelled = findLed()
	#orientSkateByLed(labelsk8, labelsk8)

	return mask, labelsclustered

def combineLabels(labels, cls):
	pts = []
	for label in labels:
		_,x,y,_,_,_,_ = labels
		pts.append((x,y))
	hull = cv2.convexHull(pts)
	rect = cv2.minAreaRect(hull)
	(cx,cy), (w,h), a = rect
	label = [cls,cx,cy,w,h,a,0]
	return label

def choosePolygonBySize(polys, cls, dim, maxcount):
	pass

def clusterLabels(labels, values):
	_,_,_,_, dist, nwn, nwx = values

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
			labeldict['label'][lbl.cls] = 1
			clusteredlabels.append(labeldict['label'])

	return clusteredlabels

#	rect, pts for each cluster
#	qualify by size, choose one


def findWheels(full, values, cls):
	#wdn, wdx, htn, htx,_,_,_ = values 
	gray = cv2.cvtColor(full, cv2.COLOR_BGR2GRAY)
	gavg = np.mean(gray)
	lower = 0

	# see google sheets "Wheels Regression Line" for this equation
	upper = (.191 * gavg + 11.2)

	# the following two lines produce equivalent results when lower is 0
	mask = cv2.inRange(gray, lower, upper)
	t, mask = cv2.threshold(gray, upper, 255, cv2.THRESH_BINARY_INV)

	# make labels list of wheels qualified by size
	labels = qualifyContours(mask,cls,values)

	# cluster
	#clusters = cluster(labels)
	#print(clusters)


	# cluster the centerpoints of the wheels
	# choose the cluster of the sk8
	# make tiny image as box around the centerpoint of the chosen cluster
	# within the tiny image
	# 	make a convex hull of the wheels
	# 	take rrect
	# 	find the led, adjust the heading of the sk8

	


	return mask,labels

def findDonutWhite(full, values, cls):
	gray, wd, ht = values
	dim = (wd,ht)

	imgMask = cv2.cvtColor(full, cv2.COLOR_BGR2GRAY)
	imgMask = cv2.GaussianBlur(imgMask,(11,11),0)

	if gray == 0:
		t, imgMask = cv2.threshold(imgMask, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	else:
		t, imgMask = cv2.threshold(imgMask, gray, 255, cv2.THRESH_BINARY)
	
	kernelsize = 3
	dilateiter = 3
	kernel = np.ones((kernelsize, kernelsize))
	imgMask = cv2.dilate(imgMask, kernel, iterations=dilateiter)
	imgMask =  cv2.erode(imgMask, kernel, iterations=dilateiter)

	rects = chooseContourBySize(imgMask,cls,dim, 1)

	return imgMask, rects

def qualifyContours(img, cls, values):
	wdn,wdx,htn,htx,_,_,_ = values
	lower = np.array((wdn,htn))
	upper = np.array((wdx,htx))
	qualified = []
	cnts,_ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		label = lbl.labelFromRect(cls, rect)
		_,_,_,w,h,_,_ = label
		size = np.array((w,h))
		if all(size >= lower) and all(size <= upper):
			qualified.append(label)
	return qualified
	
def choosePolygonBySize(polys, cls, dim, maxcount):
	qualified = []
	armse = []
	for poly in polys:
		rect = cv2.minAreaRect(poly) 
		size = rect[1]
		rmse = score.calcRMSE(dim, size)
		armse.append(rmse)
		label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
		qualified.append(label)

	# sort the labels ascending by error
	sortqualified = sorted(qualified, key=lambda a: a[lbl.scr])

	# choose the label with lowest error
	if len(sortqualified) <= 0:
		lowlabel = [0,0,0,0,0,0,0]
	else:
		lowlabel = sortqualified[0]

		# convert error to probability
		lowerror = lowlabel[lbl.scr]
		maxerror = max(armse)
		prob = score.calcProbability(lowerror, maxerror)
		lowlabel[lbl.scr] = prob
	return lowlabel
	
def chooseContourBySize(img, cls, dim, maxcount):
	qualified = []
	cnts,_ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	armse = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		size = rect[1]
		rmse = score.calcRMSE(dim, size)
		armse.append(rmse)
		label = lbl.labelFromRect(cls, rect, which=False, score=rmse)
		qualified.append(label)

	# sort the labels ascending by error
	sortqualified = sorted(qualified, key=lambda a: a[lbl.scr])

	# choose the label with lowest error
	if len(sortqualified) <= 0:
		lowlabel = [0,0,0,0,0,0,0]
	else:
		lowlabel = sortqualified[0]

		# convert error to probability
		lowerror = lowlabel[lbl.scr]
		maxerror = max(armse)
		prob = score.calcProbability(lowerror, maxerror)
		lowlabel[lbl.scr] = prob
	return lowlabel
	
def cutout(img, rect, square=None):
	ctr, size, a = rect
	if square:
		size = square
	[l,t] = ctr - size
	[r,b] = ctr + size
	l,t,r,b = np.intp([l,t,r,b])
	l,t,r,b = bbox
	return img[t:b, l:r]
	
def readAllFrames(idir, ext):
	jlist = detect.getFrameList(idir)
	if jlist[0] == '00000':
		jlist.pop(0) # remove the background 00000 frame
	ndx = 0
	lastframe = len(jlist)-1
	fulls = []
	grays = []
	while ndx <= lastframe:
		# open jpg
		fnum = jlist[ndx]
		full = cv2.imread(fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
		fulls.append(full)
		gray = cv2.cvtColor(full, cv2.COLOR_BGR2GRAY)
		grays.append(gray)
		ndx += 1
	return fulls, grays

def processAllFrames(fulls, values, cls):
	masks = []
	labels = []
	for full in fulls:
		mask,label = findSk8(full, values, cls)
		masks.append(mask)
		labels.append(label)
	return masks, labels

def calcColors(gvalues, shape, cols):

	# calculate color ranges
	hn,hx,sn,sx,vn,vx,wdn,wdx,htn,htx = gvalues	
	h = hn + int((hx-hn)/2)
	s = sn + int((sx-sn)/2)
	v = vn + int((vx-vn)/2)
	colormin = draw.BGRfromHSV(hn,sn,vn)
	colormax = draw.BGRfromHSV(hx,sx,vx)
	colornow = draw.BGRfromHSV(h,s,v)
	colors = [colormin,colornow,colormax]

	cimgmin = draw.createImage(shape, colormin)
	cimgmax = draw.createImage(shape, colormax)
	cimgnow = draw.createImage(shape, colornow)
	blank   = draw.createImage(shapecolor=(255,255,255))
	cimgs = [colormin,colornow,colormax]
	for n in range(len(cimgs), cols):
		cimgs.append(blank)
	return colors, cimgs

def annotateAll(imgs, labels):
	aimgs = []
	for n in range(0,len(imgs)):
		aimg = draw.drawImage(imgs[n], labels[n])
		aimgs.append(aimg)
	return aimgs

def main():
	global gargs,gimage,gwindowname, gvalues, gflag
	idir = 'photos/20231216-092941/bestof'
	iext = '.jpg'
	bgnum = '00000'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'      ,default=idir      ,help='input directory'        )
	parser.add_argument('-ie' ,'--iext'      ,default=iext      ,help='input file extension'   )
	parser.add_argument('-bg' ,'--background',default=bgnum     ,help='background frame number')
	parser.add_argument('-db' ,'--debug'     ,default=False, action='store_true'   ,help='show detailed info for debugging')
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# create the trackbar window
	cv2.namedWindow( gwindowname, cv2.WINDOW_NORMAL)
	cv2.resizeWindow(gwindowname, gwindowsize[0], gwindowsize[1]) 
	addTrackbars(gwindowname, gsk8specs, gvalues, onTrackbar, onMouse)
	gvalues = readTrackbars(gwindowname, gsk8specs)
	gflag = True

	# read all the frames
	fulls,grays = readAllFrames(gargs.idir, gargs.iext)

	# loop 
	while True:
		if gflag is True:
			gflag = False
			masks,labels = processAllFrames(fulls, gvalues, 2)
			afulls = annotateAll(fulls, labels)
			gimage = draw.stack(grays+masks+afulls, cols=len(fulls))
			cv2.imshow(gwindowname, gimage)

		key = cv2.waitKey(1)
		if key & 0xFF == ord('q'):
			break
		if key & 0xFF == ord('p'):
			print(gvalues)

def onTrackbar(newvalue):
	global gvalues, gflag
	gvalues = readTrackbars(gwindowname, gsk8specs)
	gflag = True 

def onMouse(event, x, y, flags, param):
	return
	global gvalues, gflag
	if event == cv2.EVENT_LBUTTONDOWN:
		# draw circle here (etc...)
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
		gvalues[0:6] = np.intp([hn,hx,sn,sx,vn,vx])
		setTrackbars(gwindowname, gsk8specs, gvalues)
		gflag = True 


if __name__ == "__main__":
	main()
