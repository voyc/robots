'''
simdiff.py - apply absdiff to each image to isolate the vehicle
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

def join(path, base, ext):
	if gargs.iext[0] != '.':
		gargs.iext = '.' + gargs.iext
	return os.path.join(path,base+ext)

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

	bg = cv2.imread(join(gargs.idir, gargs.background, gargs.iext), cv2.IMREAD_UNCHANGED)

	# loop jpgs
	image_folder = gargs.idir
	jlist = detect.getFrameList(image_folder)
	ndx = 0
	lastframe = len(jlist)-1
	while ndx <= lastframe:
		# open jpg
		fnum = jlist[ndx]
		img = cv2.imread(join(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)

		imgDiff = cv2.absdiff(img, bg)
		imgGray = cv2.cvtColor(imgDiff, cv2.COLOR_BGR2GRAY)

		imgBlur = cv2.GaussianBlur(imgGray,(11,11),0)

		t, imgMask = cv2.threshold(imgBlur, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
		
		kernelsize = 3
		dilateiter = 3
		kernel = np.ones((kernelsize, kernelsize))
		imgDilate = cv2.dilate(imgMask, kernel, iterations=dilateiter)

		# get contours
		imgLabeled = copy.deepcopy(img)
		imgMaskLabeled = copy.deepcopy(imgMask)
		imgMaskLabeled = cv2.cvtColor(imgMaskLabeled, cv2.COLOR_GRAY2BGR)
		cnts,_ = cv2.findContours(imgDilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		polys = []
		boxes = []
		square = [50,50]
		upper = [60,100]
		lower = [40, 50]
		if gargs.debug:
			upper = [80,120]
			lower = [30, 40]
		a = 0
		saverect = []
		for cnt in cnts:
			rect = cv2.minAreaRect(cnt)
			(cx,cy), (w,h),a = rect
			if w > h:
				h,w = rect[1]
				a += 90
			a = np.intp(a)
				
			if detect.inRange((w,h), lower, upper):
				saverect = rect
				poly = cv2.boxPoints(rect)
				poly = np.intp(poly)
				polys.append(poly)
				ctr = np.array(rect[0])
				[l,t] = ctr - square
				[r,b] = ctr + square
				l,t,r,b = np.intp([l,t,r,b])
				boxes.append([l,t,r,b])
				imgLabeled = cv2.rectangle(imgLabeled, (l,t), (r,b), (0,255,255), 1)
				imgMaskLabeled = cv2.rectangle(imgMaskLabeled, (l,t), (r,b), (0,255,255), 1)
		cv2.drawContours(imgLabeled, polys, -1, (0,0,255), 1) 
		cv2.drawContours(imgMaskLabeled, polys, -1, (0,0,255), 1) 

		title = f'{gargs.idir} {fnum} {len(cnts)}/{len(polys)} {a}'
		if gargs.debug:
			if len(polys) > 0:
				title = f'{fnum} {len(cnts)}/{len(polys)} {saverect}'
			key = draw.showImage(img, imgDiff, imgDilate, imgBlur, imgMask, imgDilate, imgMaskLabeled, imgLabeled, title=title)
		else:
			key = draw.showImage(imgLabeled, title=title)

		# animate and allow manual interaction
		if key & 0xFF == ord('q'):	# quit
			break
		elif key & 0xFF == ord('n'):	# next
			ndx += 1
			if ndx > lastframe:
				ndx = 0
		elif key & 0xFF == ord('p'):	# prev
			ndx -= 1
			if ndx < 0:
				ndx = lastframe


if __name__ == "__main__":
	main()
