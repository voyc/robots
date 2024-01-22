'''
simRunningDiff.py - simulte the camera, take a diff between each frame and the previous
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
		return None,0
	fnum = gframelist[gframendx]
	frame = cv2.imread(frm.fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
	gframendx += 1
	return frame,fnum

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

def preprocessMask(mask):
	kernelsize = 3
	dilateiterations = 3
	kernel = np.ones((kernelsize, kernelsize))
	mask = cv2.dilate(mask, kernel, iterations=dilateiterations)
	#mask = cv2.erode(mask, kernel, iterations=dilateiterations)
	return mask

def looper():
	previousframe,_ = getFrame()
	diffs = []
	masks = []
	labelsets = []
	aframes = []
	framecnt = 0
	
	while True:
		frame,fnum = getFrame()
		if frame is None:
			break;
		framecnt += 1

		diff = diffFrames(frame, previousframe)
		diffs.append(diff)

		gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
		t, mask = cv2.threshold(gray, 0,  255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
		mask = preprocessMask(mask)
		masks.append(mask)

		labels = labelsFromMask(mask, 2, (50,70), 1)
		labelsets.append(labels)
		if gargs.olabelsufx:
			labl.write(labels,frm.fqjoin(gargs.idir, fnum, gargs.olabelsufx))

		aframe = draw.drawImage(frame,labels,options={"title":fnum})
		aframes.append(aframe)

		if gargs.nthshow > 0 and (framecnt) % gargs.nthshow  == 0:
			key = draw.showImage(aframes, fps=gargs.fps)
			aframes = []
			#draw.showImage(diffs+masks+aframes, cols=len(aframes))
			if key & 0xFF == ord('q'):	# quit
				break
			elif key & 0xFF == ord('n'):	# next
				pass

		previousframe = frame

	cv2.destroyAllWindows()

def main():
	global gargs
	defidir = 'photos/20231216-092941/'  # day
	defiext = 'jpg'
	defnthshow = 0
	deffps = 0
	defolabelsufx = 'label.csv'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'                ,default=defidir      ,help='input folder'        )
	parser.add_argument('-ie' ,'--iext'                ,default=defiext      ,help='input extension'     )
	parser.add_argument('-ns' ,'--nthshow'   ,type=int ,default=defnthshow   ,help='stop and refresh UI every nth frame'   )
	parser.add_argument('-fps','--fps'       ,type=int ,default=deffps       ,help='fps, when nthshow is 0'   )
	parser.add_argument('-ol' ,'--olabelsufx'          ,default=defolabelsufx,help='suffix of output label file'   )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	looper()

if __name__ == "__main__":
	main()
