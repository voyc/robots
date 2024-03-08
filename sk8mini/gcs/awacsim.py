'''
awacsim.py - awacs simulator module
get an aerial photo from the disk instead of the camera
'''

import os
import cv2
import logger

framepath = '/home/john/media/webapps/sk8mini/awacs/photos/20231216-092941/'
framelist = []
framendx = 0

def getFrameList(path, nozero=True):
	flist = []
	for filename in os.listdir(path):
		fnum, ext = os.path.splitext(filename)
		if ext == '.jpg':
			flist.append(fnum)
	slist = sorted(flist)
	if nozero and slist[0] == '00000':
		slist.pop(0)
	return slist

def getFrame():
	global framendx
	if framendx >= len(framelist):
		return []
	fnum = framelist[framendx]
	framendx += 1
	fname = framepath + fnum + '.jpg'
	frame = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
	return frame, fnum

def getGroundTruth(fnum):
	fname = framepath + fnum + '.jpg'

	frame = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
	return frame, fnum
	

def setup(folder):
	global framelist, framepath
	framepath = folder
	framelist = getFrameList(framepath)
	return True
