'''
testdetect.py - test the detect library

'''

import numpy as np
import cv2
from datetime import datetime
import sys
import json
import argparse
import logging
import os

import model as mod
import detect
import label as lab

spec = None  # dict containing command-line parameters, initialized in main()

def detectObjectsMurtaza(img, settings):
	# originally taken from tello murtaza
	# See robots/autonomy/hippoc.py and https://www.youtube.com/watch?v=aJsPsY1hIhop

	# fixed settings
	gaus1 = 7
	gaus2 = 7
	gausblur = 1
	dilate1 = 5
	dilate2 = 5
	dilateiter = 1

	# initialize intermediate images
	#width, height, depth = img.shape
	imgMask = np.zeros((img.shape), np.uint8)
	imgMask[:,:] = (0,0,255)    # (B, G, R)
	imgMasked = imgMask.copy()
	imgBlur = imgMask.copy() 
	imgGray = imgMask.copy() 
	imgCanny = imgMask.copy() 
	imgDilate = imgMask.copy() 
	imgMap = img.copy()

	# algo = 0: hsv mask
	# algo = 1: hsv mask plus blur and canny
	# algo = 2: grayscale mask
	# algo = 3: grayscale mask plus blur and canny

	if settings['algo']  <= 1:  # hsv threshholds
		# mask based on hsv ranges
		lower = np.array([settings['hue_min'],settings['sat_min'],settings['val_min']])
		upper = np.array([settings['hue_max'],settings['sat_max'],settings['val_max']])
		imgThreshold = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
		imgMask = cv2.inRange(imgThreshold,lower,upper)
		imgEdged = imgMask.copy()   # skip steps 2,3,4,5,6

	elif settings['algo'] == 2 or settings['algo'] == 3:   # grayscale threshholds
		imgThreshold = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		ret, imgMask = cv2.threshold(imgThreshold, settings['gray_min'], settings['gray_max'], cv2.THRESH_BINARY)
		imgEdged = imgMask.copy()
		
	if settings['algo']  == 1 or settings['algo']  == 3:   # blur and canny 
		# step 2. apply the mask to the original.  no settings.
		imgMasked = cv2.bitwise_and(img,img, mask=imgMask)

		# step 3. apply Gaussian Blur.  settings fixed.
		imgBlur = cv2.GaussianBlur(imgMasked, (gaus1, gaus2), gausblur)

		# step 4. convert to grayscale.  no settings.
		imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_BGR2GRAY)

		# step 5. canny edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
		imgCanny = cv2.Canny(imgGray, settings['canny_lo'], settings['canny_hi'])

		# step 6. dilate, thicken, the edge lines.  settings fixed.
		kernel = np.ones((dilate1, dilate2))
		imgDilate = cv2.dilate(imgCanny, kernel, iterations=dilateiter)
		imgEdged = imgDilate.copy()


	# step 7. find countours.  get an array of polygons, one for each object.
	# work with a copy because supposedly findContours() alters the image
	contours, _ = cv2.findContours(imgEdged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

	# find box of each contour and qualify by size
	annotate = []
	for contour in contours:
		area = cv2.contourArea(contour)
		peri = cv2.arcLength(contour, True)
		approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
		x, y, w, h = cv2.boundingRect(approx)
		cx = x + int(w/2)
		cy = y + int(h/2)
		r = int((w+h)/2) 
		if r > settings['r_min'] and r < settings['r_max']:
			cls = settings['cls']
			annotate.append([cls,x,y,w,h,cx,cy,r])	

	# draw the boxes on the original map
	for a in annotate:
		color = (0,0,255) 
		thickness = 2
		cls = a[0]
		x = a[1]
		y = a[2]
		w = a[3]
		h = a[4]
		imgMap = cv2.rectangle(imgMap, (x,y), (x+w,y+h), color, thickness) 

	cv2.putText(imgMask,   'Mask',   (20,20), cv2.FONT_HERSHEY_PLAIN, 2, (255,255,255))
	cv2.putText(imgMasked, 'Masked', (20,20), cv2.FONT_HERSHEY_PLAIN, 2, (255,255,255))
	cv2.putText(imgBlur,   'Blur',   (20,20), cv2.FONT_HERSHEY_PLAIN, 2, (255,255,255))
	cv2.putText(imgGray,   'Gray',   (20,20), cv2.FONT_HERSHEY_PLAIN, 2, (255,255,255))
	cv2.putText(imgCanny,  'Canny',  (20,20), cv2.FONT_HERSHEY_PLAIN, 2, (255,255,255))
	cv2.putText(imgDilate, 'Dilate', (20,20), cv2.FONT_HERSHEY_PLAIN, 2, (255,255,255))

	return annotate, [imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate, imgMap]

#--------------- manual model initialization, aka "settings" ----------------------------------------# 

def empty(a): # passed to trackbar
	pass

def openSettings(settings):
	barmax = {
		'algo'     : 3,
		'hue_min'  : 255,
		'hue_max'  : 255,
		'sat_min'  : 255,
		'sat_max'  : 255,
		'val_min'  : 255,
		'val_max'  : 255,
		'gray_min' : 255,
		'gray_max' : 255,
		'canny_lo' : 255,
		'canny_hi' : 255,
		'r_min'    : 90,
		'r_max'    : 90,
	}
	window_name = f'{settings["name"]} settings'
	cv2.namedWindow( window_name, cv2.WINDOW_NORMAL)
	cv2.resizeWindow(window_name, 600, 240) 
	for setting in settings:
		if setting != 'name' and setting != 'cls':
			cv2.createTrackbar(setting, window_name, settings[setting], barmax[setting], empty)

def readSettings(settings):
	window_name = f'{settings["name"]} settings'
	for setting in settings:
		if setting != 'name' and setting != 'cls':
			settings[setting] = cv2.getTrackbarPos(setting, window_name)

def stackImages(scale,imgArray):
	rows = len(imgArray)
	cols = len(imgArray[0])
	rowsAvailable = isinstance(imgArray[0], list)
	width = imgArray[0][0].shape[1]
	height = imgArray[0][0].shape[0]
	if rowsAvailable:
		for x in range ( 0, rows):
			for y in range(0, cols):
				if imgArray[x][y].shape[:2] == imgArray[0][0].shape [:2]:
					imgArray[x][y] = cv2.resize(imgArray[x][y], (0, 0), None, scale, scale)
				else:
					imgArray[x][y] = cv2.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale, scale)
				if len(imgArray[x][y].shape) == 2: imgArray[x][y]= cv2.cvtColor( imgArray[x][y], cv2.COLOR_GRAY2BGR)
		imageBlank = np.zeros((height, width, 3), np.uint8)
		hor = [imageBlank]*rows
		hor_con = [imageBlank]*rows
		for x in range(0, rows):
			hor[x] = np.hstack(imgArray[x])
		ver = np.vstack(hor)
	else:
		for x in range(0, rows):
			if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
				imgArray[x] = cv2.resize(imgArray[x], (0, 0), None, scale, scale)
			else:
				imgArray[x] = cv2.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None,scale, scale)
			if len(imgArray[x].shape) == 2: imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
		hor= np.hstack(imgArray)
		ver = hor
	return ver

#--------------- main loop ----------------------------------------# 

# one image one cls
def processImageClass(img, model, cls):
	req = 'next'
	if spec.manual:
		openSettings(model[cls])
		while True:
			readSettings(model[cls])
			labels,images = detect.detectObjectsMurtaza(img, model[cls])

			# show the images
			imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate, imgMap = images
			stack = stackImages(0.7,([img,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap]))
			cv2.imshow('Image Processing', stack)
			key = cv2.waitKey(1)
			if key & 0xFF == ord('q'):	# quit
				req = 'quit'
				break
			elif key & 0xFF == 13:		# return, next image
				req = 'next'
				break
		cv2.destroyAllWindows()
	else:
		labels,_ = detect.detectObjectsMurtaza(img, model[cls])
	return labels, req

def main():
	global spec

	example_folder = '/home/john/media/webapps/sk8mini/awacs/photos/bigtrain/'
	#example_image = '00033.jpg'
	#example_model = 'model.json'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=example_folder                                     ,help='input folder.'                                              ),
	parser.add_argument('-of' ,'--ofolder'        ,default=''                                                 ,help='output folder. default to input folder.'                    ),
	parser.add_argument('-ii' ,'--iimage'         ,default='all'                                              ,help='input image filename.'                                      ),
	parser.add_argument('-oi' ,'--oimage'         ,default=''                                                 ,help='output image filename. not in use.'                         ),
	parser.add_argument('-im' ,'--imodel'         ,default='model.json'                                       ,help='input model filename.'                                      ),
	parser.add_argument('-om' ,'--omodel'         ,default='newmodel.json'                                    ,help='output model filename. default to input model.'             ),
	parser.add_argument('-ia' ,'--itruthsufx'     ,default='_truth'                                           ,help='input label filename suffix.'                                   ),
	parser.add_argument('-oa' ,'--olabelsufx'     ,default='_label'                                           ,help='output label filename suffix.'                                  ),
	parser.add_argument('-c'  ,'--cls'            ,default='all'                                              ,help='name of classifier to be processed. default to "all".'      ),
	parser.add_argument('-v'  ,'--verbose'        ,default=False                ,action='store_true'          ,help='display additional output messages.'                        ),
	parser.add_argument('-q'  ,'--quiet'          ,default=False                ,action='store_true'          ,help='suppresses all output.'                                     ),
	parser.add_argument('-m'  ,'--manual'         ,default=False                ,action='store_true'          ,help='let user initialize the model manually'                     ),
	parser.add_argument('-t'  ,'--train'          ,default=False                ,action='store_true'          ,help='train the model.'                                           ),
	spec = parser.parse_args()	# returns Namespace object, use dot-notation

	# set defaults for missing params
	if spec.ifolder != '' and spec.ifolder[len(spec.ifolder)-1] != '/':
		spec.ifolder += '/'
	if spec.ofolder == '':
		spec.ofolder = spec.ifolder
	if spec.oimage == '':
		spec.oimage = spec.iimage
	if spec.omodel == '':
		spec.omodel = spec.imodel

	# logging
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if spec.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if spec.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(spec)

	# read model
	fname = spec.ifolder+spec.imodel
	model = mod.read(fname)

	# loop all images in folder
	req = 'next'
	totalerror = 0
	numfiles = 0
	for filename in os.listdir(spec.ifolder):
		if spec.iimage == 'all' or spec.iimage == filename: 
			basename, ext = os.path.splitext(filename)
			if ext == '.jpg': 
				labels = []
				fname = spec.ifolder+filename
				img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
				logging.info(f'reading image from {fname}')
				logging.debug(f'image shape: {img.shape}')
				if spec.train:
					truth = lab.read(spec.ifolder+basename+spec.itruthsufx+'.csv')

				# loop classes for in model
				for m in model:
					if spec.cls == 'all' or spec.cls == m:
						label,req = processImageClass(img, model, m)
						labels += label
					if req == 'quit':
						break
				if spec.train:
					error = score.score(truth, labels)
					totalerror += error
					numfiles += 1
					logging.debug(f'{numfiles} {basename} error: {error}')
				lab.write(labels, spec.ofolder+basename+spec.olabelsufx+'.csv')
		if req == 'quit':
			break;

	if spec.train:
		meansqarederror = int(totalerror / numfiles)
	if spec.manual or spec.train:
		mod.write(model, spec.ofolder+spec.omodel)

if __name__ == "__main__":
	main()
