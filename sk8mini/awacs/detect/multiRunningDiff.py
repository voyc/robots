'''
makeBackground.py - make a background image by comparing from two input images
'''
import cv2
import numpy as np
import os
import argparse
import copy

import detect
import draw

gargs = None

def inRange( a, lower, upper):
	return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

def main():
	global gargs
	idir = 'photos/20231216-092941/bestof'  # day

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'    ,default=idir        ,help='input folder'        )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# two input files
	jlist = detect.getFrameList(gargs.idir)
	img1 = cv2.imread(os.path.join(gargs.idir, jlist[0] + '.jpg'), cv2.IMREAD_UNCHANGED)
	img2 = cv2.imread(os.path.join(gargs.idir, jlist[len(jlist)-1] + '.jpg'), cv2.IMREAD_UNCHANGED)

	# diff
	imgDiff = cv2.absdiff(img1, img2)	
	imgDiff2 = cv2.absdiff(img2, imgDiff)
	imgDiff3 = cv2.absdiff(img1, imgDiff2)

	imgDiff2a = cv2.absdiff(img1, imgDiff)
	imgDiff4 = cv2.absdiff(img2, imgDiff2a)

	# convert diff to mask
	imgGray = cv2.cvtColor(imgDiff, cv2.COLOR_BGR2GRAY)
	t, imgMask = cv2.threshold(imgGray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	
	draw.showImage(imgDiff, imgDiff2, imgDiff3, imgDiff4)
	return

	# get contours
	imgLabeled = copy.deepcopy(imgDiff)
	cnts,_ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	polys = []
	boxes = []
	square = [50,50]
	upper = [60,100]
	lower = [40, 50]
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt)
		(w,h) = rect[1]
		if w > h:
			h,w = rect[1]
		if inRange((w,h), lower, upper):
			poly = cv2.boxPoints(rect)
			poly = np.intp(poly)
			polys.append(poly)
			ctr = np.array(rect[0])
			[l,t] = ctr - square
			[r,b] = ctr + square
			l,t,r,b = np.intp([l,t,r,b])
			boxes.append([l,t,r,b])
			imgLabeled = cv2.rectangle(imgLabeled, (l,t), (r,b), (0,255,255), 1)
	cv2.drawContours(imgLabeled, polys, -1, (0,0,255), 1) 

	print(f'contours {len(cnts)}')
	print(f'polys {len(polys)}')
	print(f'boxes {len(boxes)}')

	# have two boxes, swap one of them
	l,t,r,b = boxes[0]
	tempimg1 = img1[t:b,l:r]
	#l,t,r,b = boxes[1]
	#tempimg2 = img1[t:b, l:r]

	imgBack1 = copy.deepcopy(img1)
	imgBack1[t:b, l:r] = img2[t:b, l:r]

	imgBack2 = copy.deepcopy(img2)
	imgBack2[t:b, l:r] = img1[t:b, l:r]

	#draw.showImage(tempimg1, tempimg2j)


	draw.showImage(img1, img2, imgDiff, imgMask, imgLabeled, imgBack1, imgBack2)

	ans = input("Which is the correct background image? 1/2: ")
	if ans == 1:
		imgBack = imgBack1
	else:
		imgBack = imgBack2

	# write the finished background image
	fqname = os.path.join(gargs.idir, 'background.jpg')
	cv2.imwrite(fqname, imgBack) 

if __name__ == "__main__":
	main()
