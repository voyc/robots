'''
simtiny.py - like simdiff, then isolate square around vehicle for further analysis
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
gwin = 'named window'

#------------- add to draw.py  ------------------
def empty(a): # passed to trackbar by default
	pass

specs = [
	{ "name":"min_hue", "value": 120, "upper": 180 },
	{ "name":"max_hue", "value": 138, "upper": 180 },
	{ "name":"min_sat", "value":   0, "upper": 255 },
	{ "name":"max_sat", "value": 255, "upper": 255 },
	{ "name":"min_val", "value":   0, "upper": 255 },
	{ "name":"max_val", "value": 255, "upper": 255 },
]

def openSettings(modcls):
	global gwin
	gwin = f'{modcls["name"]} settings'
	cv2.namedWindow( gwin, cv2.WINDOW_NORMAL)
	cv2.resizeWindow(gwin, 1200, 600) 
	specs = modcls['spec']
	for spec in specs:
		name = spec['name']
		value = spec['value']
		upper = spec['upper']
		cv2.createTrackbar(name, gwin, value, upper, empty)

def readSettings(modcls):
	specs = modcls['spec']
	for spec in specs:
		spec['value'] = cv2.getTrackbarPos(spec['name'], gwin)

def fqjoin(path, base, ext):
	if gargs.iext[0] != '.':
		gargs.iext = '.' + gargs.iext
	return os.path.join(path,base+ext)

#------------- add to draw.py  ------------------

def main():
	global gargs
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

	bg = cv2.imread(fqjoin(gargs.idir, gargs.background, gargs.iext), cv2.IMREAD_UNCHANGED)

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
	cols = len(tinys)
	key = draw.showImage(tinys+masks+grays+cannys, title='tinys', cols=4)

if __name__ == "__main__":
	main()
