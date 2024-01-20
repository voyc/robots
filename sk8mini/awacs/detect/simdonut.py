'''
simdonut.py - find the donut
'''
import cv2
import numpy as np
import os
import argparse
import copy

import draw
import detect

gargs = None

def inRange( a, lower, upper):
	return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

def findRect(mask):
	amask = copy.deepcopy(mask)
	upper = [60,100]
	lower = [40, 50]
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 
	polys = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt)
		size = rect[1]
		print(size)
		if False:  #True: #inRange(size, lower, upper):
			print(rect)
			poly = cv2.boxPoints(rect)
			print(poly)
			polys.append(poly)
			cv2.drawContours(amask, polys, 0, (0,0,255), 1)
			
	return amask

def findDonut(img):
	mask = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

	(T, totsu) = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	(T, totsu) = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

	amean = cv2.adaptiveThreshold(mask, 255, cv2.ADAPTIVE_THRESH_MEAN_C,     cv2.THRESH_BINARY_INV, 21, 3)
	agaus = cv2.adaptiveThreshold(mask, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 4)

	amask = findRect(agaus)

	#return img
	#return mask
	#return totsu
	#return amean
	#return agaus
	return amask

def main():
	global gargs
	idir = 'photos/training'  # day

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'    ,default=idir        ,help='input folder'        )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# loop jpgs
	image_folder = gargs.idir
	jlist = detect.getFrameList(image_folder)
	ndx = 0
	lastframe = len(jlist)-1
	a = []
	while ndx <= lastframe:
		fnum = jlist[ndx]
		fqname = os.path.join(image_folder, fnum + '.jpg')
		img = cv2.imread(fqname, cv2.IMREAD_UNCHANGED)
		mask = findDonut(img)
		a.append(mask)
		ndx += 1

	draw.showImage(a)

if __name__ == "__main__":
	main()
