'''
sim.py - simulate realtime object detection
'''
import cv2
import numpy as np
import os
import argparse

import detect 
import label as labl
import draw
import model as modl

day_model = [
{
	"cls": 1,
	"name": "cone",
	"algo": 0,
	"rotate": 0,
	"values": [0, 86, 134, 255, 101, 196, 11, 26, 11, 26]
},
{
	"cls": 2,
	"name": "led",
	"algo": 1,
	"rotate": 0,
	"values": [158, 5, 8, 5, 8]
},
{
	"cls": 3,
	"name": "sk8",
	"algo": 0,
	"rotate": 1,
	"values": [31, 56, 48, 114, 22, 177, 35, 69, 59, 92]
}
]
night_model = [
{
	"cls": 1,
	"name": "cone",
	"algo": 0,
	"rotate": 0,
	"values": [0, 69, 108, 156, 77, 148, 14, 40, 15, 40] 
},
{
	"cls": 2,
	"name": "led",
	"algo": 1,
	"rotate": 0,
	"values": [158, 5, 8, 5, 8] 
},
{
	"cls": 3,
	"name": "sk8",
	"algo": 0,
	"rotate": 1,
	"values": [0, 63, 33, 58, 22, 177, 7, 68, 44, 152] 
}
]

def getWheels(image):
	image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	ret, imgWheelMask = cv2.threshold(image, 23, 255, cv2.THRESH_BINARY_INV)
	return imgWheelMask

'''
1. locate the cones
2. locate the vehicle and crop it
	option a. use diff
	option b. use donut
3. within crop, get to a rotated rect with accurate heading 
	options
		a. remove donut
		b. remove wheels
		c. remove shadows

experiments
	find vehicle with diff mask
	find cones with interpolated values
	find donut with interpolated values

ideas
	write program to make background for folder (similar to cv2.createBackgroundRemover()
		input two images
	if we use donut, we have only center until vehicle has moved 1 length
	if we use diff, we have to start with vehicle off screen
	write simdifr.py to test diff on full arena
	write interpolation experiments

'''

backgroundImage = None
backgroundStep = 0
backgroundBbox = []

def goBaby(imgBgr, labels):
	global backgroundBbox, backgroundImage, backgroundStep

	# find the donut
	donut = None
	counts  = [0,0,0,0,0,0,0,0]
	for label in labels:
		cls, cx,cy,w,h,hdg,scr = label
		print(cls)
		counts[cls-1] += 1
		if not donut and cls in [2,3,4]:
			donut = label	
	print(donut)

	# isolate the vehicle around the donut	
	cls, cx,cy,w,h,hdg,scr = donut 
	sz = np.array([ 70, 70])
	ctr = np.array([cx,cy])
	lt = ctr - sz
	rb = ctr + sz
	l,t = lt
	r,b = rb
	imgCrop = imgBgr[t:b, l:r]
	#imgDiff = imgCrop
	#imgDiffGray = imgCrop
	#thresh = imgCrop
	#imgMasked = imgCrop


	#imgWheels = getWheels(imgCrop)


	# remove background
	if backgroundStep == 0:
		backgroundImage = imgBgr
		backgroundBbox = [l,t,r,b]
		backgroundStep += 1
	elif backgroundStep == 1:
		l,t,r,b = backgroundBbox
		backgroundImage[t:b, l:r] = imgBgr[t:b, l:r]
		backgroundStep += 1
	else:
		# remove background image from imgBgr
		imgDiff = cv2.absdiff(backgroundImage[t:b, l:r], imgBgr[t:b, l:r])	
		imgDiffGray = cv2.cvtColor(imgDiff, cv2.COLOR_BGR2GRAY)	
		_, imgMaskDiff = cv2.threshold(imgDiffGray, 5, 255, cv2.THRESH_BINARY)
		# 128 - no mask
		# 70 - wheels only (light color)
		# 25 - full vehicle plus shadows
		# 5 - lots of shadow, including the cone that is now in shadow
		# note: shadows are always on the east, because the windows are on the west
		# look at centermost cone, try values until one has a perfect circle
		# try various values until you get the right wd and ht
		backgroundStep += 1

	# here do the complete upper,lower hsv inRange
	values = [0, 126, 35, 92, 35, 102, 35, 66, 59, 94]
	[cn,cx,sn,sx,vn,vx,wn,wx,hn,hx] = values
	lower = np.array([cn,sn,vn])
	upper = np.array([cx,sx,vx])
	imgCropHsv = cv2.cvtColor(imgCrop, cv2.COLOR_BGR2HSV)
	imgMaskHsv = cv2.inRange(imgCropHsv,lower,upper)

	if backgroundStep < 3:
		imgMask = imgMaskHsv
	else:
		imgMask = imgMaskDiff

	#cnts,_ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
	#for cnt in cnts:
	#	rect = cv2.minAreaRect(cnt)
	#	print(rect)
	#	poly = cv2.boxPoints(rect)
	#	#cv2.drawContours(imgMask, [poly], 0, (0,0,255), 1)

	# canny edge detection
	imgMasked = cv2.bitwise_and(imgCrop, imgCrop, mask=imgMask)
	imgCanny = cv2.Canny(imgMasked, 50, 70)
	
	kernel = np.ones((5, 5))
	imgClosed = cv2.morphologyEx(imgCanny, cv2.MORPH_CLOSE, kernel)
	
	if backgroundStep < 3:
		imgOut = draw.stack(imgCrop, imgMaskHsv, imgCanny, imgClosed)
	else:
		imgOut = draw.stack(imgCrop, imgMaskHsv, imgDiff, imgDiffGray, imgMaskDiff, imgMasked, imgCanny, imgClosed)
	return imgOut



gargs = None

def main():
	global gargs
	idir = 'photos/20231216-092941/bestof'  # day

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'    ,default=idir        ,help='input folder'        )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# read model
	modelfqname = os.path.join(gargs.idir, 'model.json')
	model = modl.read(modelfqname)

	# loop jpgs
	image_folder = gargs.idir
	jlist = detect.getFrameList(image_folder)
	pause = True
	ndx = 0
	lastframe = len(jlist)-1
	while ndx <= lastframe:
		# open jpg
		fnum = jlist[ndx]
		fqname = os.path.join(image_folder, fnum + '.jpg')
		img = cv2.imread(fqname, cv2.IMREAD_UNCHANGED)

		# detect objects
		labels = detect.detectObjects(img,model)
		slabels = labl.format(labels, 'realtime')
		dlabels = labl.format(labels, 'display')
		#print(slabels)
		print(dlabels)

		img = goBaby(img, labels)

		# display jpg	
		#img = draw.drawImage(img,labels, {'format':'sbs'})
		#img = draw.titleImage(img,fnum)
		cv2.imshow(f'sim {gargs.idir}', img)

		# animate and allow manual interaction
		key = cv2.waitKey(0)
		if key & 0xFF == ord('q'):	# quit
			break
		elif key & 0xFF == 13:		# return, pause
			pause = not pause
		elif key & 0xFF == ord('n'):	# next
			ndx += 1
			if ndx > lastframe:
				ndx = 0
		elif key & 0xFF == ord('p'):	# prev
			ndx -= 1
			if ndx < 0:
				ndx = lastframe

		if not pause:
			ndx += 1

	cv2.destroyAllWindows()


	#labels = []
	#for m in range(2):
	#	label = detectObjects(img, model, m)
	#	labels += label

	#print(labels)



if __name__ == "__main__":
	main()
