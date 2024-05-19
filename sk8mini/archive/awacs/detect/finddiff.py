'''
finddiff.py - find difference to isolate vehicle in multiple photos
'''
import cv2
import numpy as np
import os
import argparse
import copy

import detect 
import label as labl
import draw
import model as modl

gargs = None
gimage = None
gwindowname = None
gdeckspecs = [
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
gvalues = [120,138,  0 ,255,  0,255, 30, 80, 40,120]
gflag = True

#------------- add to draw.py  ------------------

def donothing(a): # default trackbar callback
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

def findAllVehicles(idir, iext, bg):
	# loop jpgs
	image_folder = gargs.idir
	jlist = detect.getFrameList(image_folder)
	jlist.pop(0) # remove the background 00000 frame
	ndx = 0
	lastframe = len(jlist)-1
	tinys = []
	masks = []
	grays = []
	cannys = []
	while ndx <= lastframe:
		# open jpg
		fnum = jlist[ndx]
		img = cv2.imread(fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)

		imgDiff = cv2.absdiff(img, bg)
		imgGray = cv2.cvtColor(imgDiff, cv2.COLOR_BGR2GRAY)

		imgBlur = cv2.GaussianBlur(imgGray,(11,11),0)

		t, imgMask = cv2.threshold(imgBlur, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
		
		kernelsize = 3
		dilateiter = 3
		kernel = np.ones((kernelsize, kernelsize))
		imgDilate = cv2.dilate(imgMask, kernel, iterations=dilateiter)

		# get contours
		cnts,_ = cv2.findContours(imgDilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		square = [50,50]
		upper = [60,100]
		lower = [40, 50]
		if gargs.debug:
			upper = [80,120]
			lower = [30, 40]
		for cnt in cnts:
			rect = cv2.minAreaRect(cnt)
			(cx,cy), (w,h),a = rect
			if w > h:
				h,w = rect[1]
				a += 90
				
			if detect.inRange((w,h), lower, upper):
				ctr = np.array(rect[0])
				[l,t] = ctr - square
				[r,b] = ctr + square
				l,t,r,b = np.intp([l,t,r,b])
				tinys.append(img[t:b, l:r])

				mask = imgMask[t:b, l:r]
				masks.append(mask)

				gray = imgGray[t:b, l:r]
				grays.append(gray)

				canny = cv2.Canny(gray, 80,200)
				cannys.append(canny)
		ndx += 1
	return tinys, masks, grays, cannys

def examineTinys(tinys,gvalues):	

	# calculate color ranges
	hn,hx,sn,sx,vn,vx,wdn,wdx,htn,htx = gvalues	
	h = hn + int((hx-hn)/2)
	s = sn + int((sx-sn)/2)
	v = vn + int((vx-vn)/2)
	colormin = draw.createImage(shape=tinys[0].shape, color=draw.BGRfromHSV(hn,sn,vn))
	colormax = draw.createImage(shape=tinys[0].shape, color=draw.BGRfromHSV(hx,sx,vx))
	colornow = draw.createImage(shape=tinys[0].shape, color=draw.BGRfromHSV(h,s,v))
	blank = draw.createImage(shape=tinys[0].shape, color=(255,255,255))
	colors = [colormin,colornow,colormax,blank]

	masks = []
	for tiny in tinys:
		mask = cv2.inRange(tiny, colormin, colormax)
		masks.append(mask)
	return colors, masks

def main():
	global gargs,gimage,gwindowname, gvalues, gflag
	idir = 'photos/20231216-092941/bestof'
	iext = '.jpg'
	bgnum = '00095'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'      ,default=idir      ,help='input directory'        )
	parser.add_argument('-ie' ,'--iext'      ,default=iext      ,help='input file extension'   )
	parser.add_argument('-bg' ,'--background',default=bgnum     ,help='background frame number')
	parser.add_argument('-db' ,'--debug'     ,default=False, action='store_true'   ,help='show detailed info for debugging')
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	bg = cv2.imread(fqjoin(gargs.idir, gargs.background, gargs.iext), cv2.IMREAD_UNCHANGED)

	tinys, masks, grays, cannys = findAllVehicles(gargs.idir, gargs.iext, bg)

	#key = draw.showImage(tinys+masks+grays+cannys, title='tinys', cols=len(tinys))
	#return

	# create the trackbar window
	windowname = 'tweak hsv'
	cv2.namedWindow( windowname, cv2.WINDOW_NORMAL)
	cv2.resizeWindow(windowname, 900, 900) 
	addTrackbars(windowname, gdeckspecs, gvalues, onTrackbar, onMouse)
	gwindowname = windowname
	gvalues = readTrackbars(gwindowname, gdeckspecs)
	gflag = True
	#print(gvalues)
	while True:
		if gflag is True:
			gflag = False

			# calculate color ranges
			#hn,hx,sn,sx,vn,vx,wdn,wdx,htn,htx = gvalues	
			#h = hn + int((hx-hn)/2)
			#s = sn + int((sx-sn)/2)
			#v = vn + int((vx-vn)/2)
			#colormin = draw.createImage(shape=tinys[0].shape, color=draw.BGRfromHSV(hn,sn,vn))
			#colormax = draw.createImage(shape=tinys[0].shape, color=draw.BGRfromHSV(hx,sx,vx))
			#colornow = draw.createImage(shape=tinys[0].shape, color=draw.BGRfromHSV(h,s,v))
			#blank = draw.createImage(shape=tinys[0].shape, color=(255,255,255))
			#colors = [colormin,colornow,colormax,blank]

			colors, masks = examineTinys(tinys, gvalues) #colors, sizes)	

			gimage = draw.stack(colors+tinys+masks, cols=len(tinys))
			cv2.imshow(windowname, gimage)

		key = cv2.waitKey(1)
		if key & 0xFF == ord('q'):
			break
		if key & 0xFF == ord('p'):
			print(gvalues)

def onTrackbar(newvalue):
	global gvalues, gflag
	gvalues = readTrackbars(gwindowname, gdeckspecs)
	gflag = True 

def onMouse(event, x, y, flags, param):
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
		setTrackbars(gwindowname, gdeckspecs, gvalues)
		gflag = True 


if __name__ == "__main__":
	main()
