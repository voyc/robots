'''
finddonut.py - find donut, to isolate vehicle, in multiple photos

donut has a white ring with a black center

there are two ways to find a white color
	1. hsv with high sat 
	2. grayscale threshhold of high gray value, method binary

there are two ways to find a black color
	1. hsv with low value
	2. grayscale threshold of low gray value, method binary inverted
'''
import cv2
import numpy as np
import os
import argparse
import copy

import detect 
import score 
import label as labl
import draw
import model as modl

# global constants
galgo = 'white'
gwindowname = 'find donuts'
gwindowsize = (1200, 900)
gdonutspecswhite = [
	{ "name":"gray"   , "upper": 255 },
	{ "name":"width"  , "upper": 200 },
	{ "name":"height" , "upper": 200 },
]
gdonutspecshsv = [
	{ "name":"min_hue", "upper": 180 },
	{ "name":"max_hue", "upper": 180 },
	{ "name":"min_sat", "upper": 255 },
	{ "name":"max_sat", "upper": 255 },
	{ "name":"min_val", "upper": 255 },
	{ "name":"max_val", "upper": 255 },
	{ "name":"min_wd" , "upper": 200 },
	{ "name":"max_wd" , "upper": 200 },
	{ "name":"min_ht" , "upper": 200 },
	{ "name":"max_ht" , "upper": 200 }
]
gvalueshsv = [138, 180, 171, 250, 145, 222, 39, 73, 40, 120]
gvalueswhite = [0, 25, 25]

# global variables
gargs = None
gimage = None
gflag = True
gdonutspecs = None
gvalues = None

if galgo == 'white':
	gdonutspecs = gdonutspecswhite
	gvalues = gvalueswhite
elif galgo == 'hsv':
	gdonutspecs = gdonutspecshsv
	gvalues = gvalueshsv

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

def findDonutHSV(full, values, cls):
	hn,hx,sn,sx,vn,vx,wdn,wdx,htn,htx = values
	lower = (hn,sn,vn)
	upper = (hx,sx,vx)
	mask = cv2.inRange(full, lower, upper)
	dim = (wdn, htn)
	label = chooseContourBySize(mask,cls,dim,1)
	return mask,label 

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

def chooseContourBySize(img, cls, dim, maxcount):
	qualified = []
	cnts,_ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	armse = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		size = rect[1]
		rmse = score.rmse(dim, size)
		armse.append(rmse)
		label = labl.labelFromRect(cls, rect, which=False, score=rmse)
		qualified.append(label)

	# sort the labels ascending by error
	sortqualified = sorted(qualified, key=lambda a: a[labl.scr])

	# choose the label with lowest error
	lowlabel = sortqualified[0]

	# convert error to probability
	lowerror = lowlabel[labl.scr]
	maxerror = max(armse)
	prob = score.probability(lowerror, maxerror)
	lowlabel[labl.scr] = prob
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
	while ndx <= lastframe:
		# open jpg
		fnum = jlist[ndx]
		full = cv2.imread(fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
		fulls.append(full)
		ndx += 1
	return fulls

def findAllDonuts(fulls, algo, values, cls):
	masks = []
	labels = []
	for full in fulls:
		if algo == 'hsv':
			mask,label = findDonutHSV(full, values, cls)
		elif algo == 'black':
			pass
		elif algo == 'white':
			mask,label = findDonutWhite(full, values, cls)
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
		aimg = draw.drawImage(imgs[n], [labels[n]])
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
	addTrackbars(gwindowname, gdonutspecs, gvalues, onTrackbar, onMouse)
	gvalues = readTrackbars(gwindowname, gdonutspecs)
	gflag = True

	# read all the frames
	fulls = readAllFrames(gargs.idir, gargs.iext)

	# loop 
	while True:
		if gflag is True:
			gflag = False
			masks,labels = findAllDonuts(fulls, galgo, gvalues, 2)
			afulls = annotateAll(fulls, labels)
			gimage = draw.stack(fulls+masks+afulls, cols=len(fulls))
			cv2.imshow(gwindowname, gimage)

		key = cv2.waitKey(1)
		if key & 0xFF == ord('q'):
			break
		if key & 0xFF == ord('p'):
			print(gvalues)

def onTrackbar(newvalue):
	global gvalues, gflag
	gvalues = readTrackbars(gwindowname, gdonutspecs)
	gflag = True 

def onMouse(event, x, y, flags, param):
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
		setTrackbars(gwindowname, gdonutspecs, gvalues)
		gflag = True 


if __name__ == "__main__":
	main()
