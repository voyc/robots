'''
multiRunningDiff.py - take a diff between each frame and the previous
'''
import cv2
import numpy as np
import os
import argparse
import copy

import detect
import draw
import frame as frm 
import score
import label as labl

gargs = None
gframendx = 0
gframelist = []

def getFrame():
	global gframendx, gframelist
	if gframendx == 0:
		gframelist = frm.getFrameList(gargs.idir)
	if gframendx >= len(gframelist):
		return None
	if gargs.maxframes > 0 and gframendx > gargs.maxframes:
		return None
	fnum = gframelist[gframendx]
	frame = cv2.imread(frm.fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
	gframendx += 1
	return frame

def diffFrames(current,previous):
	diff = cv2.absdiff(current, previous)

	imgDiff1 = cv2.absdiff(current, previous)	
	imgDiff2 = cv2.absdiff(previous, imgDiff1)
	imgDiff3 = cv2.absdiff(current, imgDiff2)

	imgDiff2a = cv2.absdiff(current, imgDiff1)
	imgDiff4 = cv2.absdiff(previous, imgDiff2a)

	#draw.showImage(previousframe, frame, imgDiff1, imgDiff2, imgDiff2a, imgDiff3, imgDiff4)
	return imgDiff4

def labelsFromMask(mask, cls, dim, maxcount):
	labels = []
	cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	armse = []
	for cnt in cnts:
		rect = cv2.minAreaRect(cnt) 
		size = rect[1]
		rmse = score.rmse(dim, size)
		armse.append(rmse)
		label = labl.labelFromRect(cls, rect, which=False, score=rmse)
		labels.append(label)

	# sort the labels ascending by error
	sortedlabels = sorted(labels, key=lambda a: a[labl.scr])

	# take the n with lowest score
	bestlabels = sortedlabels[0:maxcount]

	# convert error to probability
	maxerror = max(armse)
	for label in bestlabels:
		rmse = label[labl.scr]
		prob = score.probability(rmse, maxerror)
		label[labl.scr] = prob
	return bestlabels

def looper():
	previousframe = getFrame()
	diffs = []
	masks = []
	labelsets = []
	aframes = []
	
	while True:
		frame = getFrame()
		if frame is None:
			break;

		diff = diffFrames(frame, previousframe)
		diffs.append(diff)

		gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

		t, mask = cv2.threshold(gray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
		kernelsize = 3
		dilateiterations = 3
		kernel = np.ones((kernelsize, kernelsize))
		mask = cv2.dilate(mask, kernel, iterations=dilateiterations)
		#mask = cv2.erode(mask, kernel, iterations=dilateiterations)
		masks.append(mask)

		labels = labelsFromMask(mask, 2, (50,70), 1)
		labelsets.append(labels)

		aframe = draw.drawImage(mask,labels)
		aframes.append(aframe)


		previousframe = frame

	draw.showImage(aframes,cols=10)
	#draw.showImage(diffs+masks+aframes, cols=len(aframes))
	return 

def main():
	global gargs
	idir = 'photos/20231216-092941/'  # day
	iext = 'jpg'
	maxframes = 0

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'    ,default=idir        ,help='input folder'        )
	parser.add_argument('-ie' ,'--iext'    ,default=iext        ,help='input extension'     )
	parser.add_argument('-mf' ,'--maxframes',type=int, default=maxframes  ,help='maximum number of frames to process'   )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	looper()
	return

	# convert diff to mask
	imgGray = cv2.cvtColor(imgDiff, cv2.COLOR_BGR2GRAY)
	t, imgMask = cv2.threshold(imgGray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
	
	draw.showImage(imgDiff, imgDiff2, imgDiff3, imgDiff4)

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
