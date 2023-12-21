'''
detect.py - object detection by image processing
originally taken from tello murtaza

The image is a numpy array.

There are multiple ways to manipulate the numpy array.
  - a python for-loop (slow)
  - a numpy vector math method (fast)
  - methods of an image processing package, like:
    . opencv: computer vision
    . matplotlib: similar to MatLab
    . scikit-learn, aka sklearn: machine learning
    . scipy: optimization, linear regression, image processing, etc.

Object detection can be done in multiple ways, including:
  . computer vision, algorithmic
  . neural net, non-algorithmic AI

The active ingredient in this program is function 
	annotate = detectObjects(image, model)

See robots/autonomy/hippoc.py and https://www.youtube.com/watch?v=aJsPsY1hIhop
'''

import numpy as np
import cv2
from datetime import datetime
import sys
import json
import argparse
import logging
import os

# globals
spec = None  # dict containing command-line parameters, initialized in main()

#--------------- image file management ----------------------------------------# 

def readImage(fname):
	img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
	logging.info(f'reading image from {fname}')
	logging.debug(f'image shape: {img.shape}')
	return img

#--------------- annotate management ----------------------------------------# 

#example_annotate = [   # input/output structure, a list of lists, saved to disk as csv
#	[1, 533, 517, 20, 20, 543, 527, 20],   # cls, x,y,w,h,cx,cy,r
#	[1, 72, 512, 31, 24, 87, 524, 27],
#	[1, 186, 407, 27, 21, 199, 417, 24],
#	[2, 482, 288, 8, 10, 486, 293, 9],
#	[2, 500, 265, 7, 11, 503, 270, 9],
#	[3, 471, 279, 30, 27, 486, 292, 28]
#]

def readAnnotate():
	return

def writeAnnotate(annotate, fname):
	with open(fname, 'w') as f:
		for a in annotate:
			f.write( f'{a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]}, {a[5]}, {a[6]}, {a[7]}\n')
	logging.info(f'writing annotate to {fname}')
	for a in annotate:
		logging.debug( f'{a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]}, {a[5]}, {a[6]}, {a[7]}')

def scoreAnnotate(train, annotate):
	error = 0
	diff = len(train) - len(annotate)
	error = diff * 10
	return error

#--------------- model management ----------------------------------------# 

#example_model = {  # input/output structure, the model, a json dict saved to disk as string
#	'cone': {
#		'name'     : 'cone',
#		'cls'    : 1,
#		'hue_min'  : 0,
#		'hue_max'  : 127,
#		'sat_min'  : 107,
#		'sat_max'  : 255,
#		'val_min'  : 89,
#		'val_max'  : 255,
#		'canny_lo' : 82,
#		'canny_hi' : 127,
#		'r_min'  :  10,
#		'r_max'  : 900,
#	},
#	'wheel': {
#		'name'     : 'wheel',
#		'cls'    : 2,
#		'hue_min'  : 0,
#		'hue_max'  : 14,
#		'sat_min'  : 107,
#		'sat_max'  : 255,
#		'val_min'  : 89,
#		'val_max'  : 255,
#		'canny_lo' : 82,
#		'canny_hi' : 127,
#		'r_min'  :  10,
#		'r_max'  : 900,
#	}
#}

def readModel(fname):
	with open(fname, 'r') as f:
		model = json.load(f)
	logging.info(f'reading model from {fname}')
	logging.debug(json.dumps(model, indent=4))
	logging.debug(f'model contains {len(model)} classifiers')
	for m in model:
		logging.debug(f'{model[m]["cls"]} {m}')
	return model

def writeModel(model, fname):
	with open(fname, 'w') as f:
		f.write(json.dumps(model, indent=4))
	logging.info(f'writing model to {fname}')
	logging.debug(json.dumps(model, indent=4))
	logging.debug(f'model contains {len(model)} classifiers')
	for m in model:
		logging.debug(f'{model[m]["cls"]} {m}')

#--------------- manual model initialization, aka "settings" ----------------------------------------# 

def empty(a): # passed to trackbar
	pass

def openSettings(settings):
	barmax = {
		'hue_min'  : 255,
		'hue_max'  : 255,
		'sat_min'  : 255,
		'sat_max'  : 255,
		'val_min'  : 255,
		'val_max'  : 255,
		'canny_lo' : 255,
		'canny_hi' : 255,
		'r_min'  : 900,
		'r_max'  : 900,
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

#--------------- image processing ----------------------------------------# 

def detectObjects(img, settings):
	# mask based on hsv ranges
	lower = np.array([settings['hue_min'],settings['sat_min'],settings['val_min']])
	upper = np.array([settings['hue_max'],settings['sat_max'],settings['val_max']])
	imgHsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

	# step 1. make a mask by HSV settings
	imgMask = cv2.inRange(imgHsv,lower,upper)

	# step 2. apply the mask to the original.  no settings.
	imgMasked = cv2.bitwise_and(img,img, mask=imgMask)

	# step 3. apply Gaussian Blur.  settings fixed.
	imgBlur = cv2.GaussianBlur(imgMasked, (7, 7), 1)

	# step 4. convert to grayscale.  no settings.
	imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_BGR2GRAY)

	# step 5. canny edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
	imgCanny = cv2.Canny(imgGray, settings['canny_lo'], settings['canny_hi'])

	# step 6. dilate, thicken, the edge lines.  settings fixed.
	kernel = np.ones((5, 5))
	imgDilate = cv2.dilate(imgCanny, kernel, iterations=1)

	# step 7. find countours.  get an array of polygons, one for each object.
	# work with a copy because supposedly findContours() alters the image
	if settings['canny_lo'] > 0:
		imgEdged = imgDilate.copy()
	else:
		imgEdged = imgMask.copy()   # skip steps 2,3,4,5,6
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
	imgMap = img.copy()
	for a in annotate:
		color = (0,0,255) 
		thickness = 2
		cls = a[0]
		x = a[1]
		y = a[2]
		w = a[3]
		h = a[4]
		imgMap = cv2.rectangle(imgMap, (x,y), (x+w,y+h), color, thickness) 

	return annotate, [imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate, imgMap]

#--------------- main loop ----------------------------------------# 

def main():
	global spec

	#example_folder = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
	#example_image = '00001.jpg'
	#example_model = 'model.json'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=''                                                 ,help='input folder.'                                              ),
	parser.add_argument('-of' ,'--ofolder'        ,default=''                                                 ,help='output folder. default to input folder.'                    ),
	parser.add_argument('-ii' ,'--iimage'         ,default='all'                                              ,help='input image filename.'                                      ),
	parser.add_argument('-oi' ,'--oimage'         ,default=''                                                 ,help='output image filename. not in use.'                         ),
	parser.add_argument('-im' ,'--imodel'         ,default='model.json'                                       ,help='input model filename.'                                      ),
	parser.add_argument('-om' ,'--omodel'         ,default=''                                                 ,help='output model filename. default to input model.'             ),
	parser.add_argument('-ia' ,'--iannosufx'      ,default='_train'                                           ,help='input annotate filename suffix.'                                   ),
	parser.add_argument('-oa' ,'--oannosufx'      ,default='_annot'                                           ,help='output annotate filename suffix.'                                  ),
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
	model = readModel(fname)

	# loop all images in folder
	firstfile = True
	totalerror = 0
	numfiles = 0
	for filename in os.listdir(spec.ifolder):
		if spec.iimage == 'all' or spec.iimage == filename: 
			basename, ext = os.path.splitext(filename)
			if ext == '.jpg': 
				annotate = []
				img = readImage(spec.ifolder+filename)
				if spec.train:
					train = readAnnotate(spec.ifolder+basename+spec.iannosufx+'.csv')

				# loop classes for in model
				for m in model:
					if spec.cls == 'all' or spec.cls == m:
						annotate += processImageClass(img, model, m, firstfile)
				if spec.train:
					error = scoreAnnotate(train, annotate)
					totalerror += error
					numfiles += 1
					logging.debug(f'{numfiles} {basename} error: {error}')
				writeAnnotate(annotate, spec.ofolder+basename+spec.oannosufx+'.csv')
				firstfile = False

	if spec.train:
		meansqarederror = int(totalerror / numfiles)
	if spec.manual or spec.train:
		writeModel(model, spec.ofolder+spec.omodel)


# one image one cls
def processImageClass(img, model, cls, firstfile):
	if spec.manual and firstfile:
		openSettings(model[cls])
		while True:
			readSettings(model[cls])
			annotate, images = detectObjects(img, model[cls])

			# show the images
			imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate, imgEdged = images
			stack = stackImages(0.7,([img,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgEdged]))
			cv2.imshow('Image Processing', stack)
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break
		cv2.destroyAllWindows()
	else:
		annotate, _ = detectObjects(img, model[cls])
	return annotate


if __name__ == "__main__":
	main()




'''
input parameters
read model
for each image
	read image
	read annotation
	loop thru classes
		detectObjects, one image, one class
			if manual, open settings for each class only on first image
	write annotation file, one image, all classes

if manual init
	run separate loop - while settings open
	one image, one class

if --manual
	on the first image, let the user initialize the model
	separately for each class

recommended usage if manual, one image, one class

mode=detect
mode=manual
mode=train

manual init of a class in a model, 
	how do you add a new class?  edit the model json file.

three different functions, depending on mode
if mode=='manual'
	manualModelInit()
if mode=='train'
	compare annotations, old and new, keep best, write out at the end
if mode=='detect'
	run one image at a time

in production,
	we want minimal code on the awacs to detect objects for each image
	therefore, we do not want scoring, annotating, manual initing, etc linked in 

detectObjects(img, model)
	img and model have both been opened already

the core loop
	walks thru the steps
	conditional compile? without all the debugging info	


manual one image one classifiers
manual one image all classifiers
manual one image all classifiers write annotation
manual one image all classifiers write annotation, read trainer annotation and calc error

loop training
	loop thru images
		read first or specifed image
		loop thru classes
			processImage()
		write annotation
		
		read next image, or exit
	write error stats
	adjust model parameter

loopTraining()
loopImages()
loopClasses()
processImage()

loopTraining()
	loopImages()
		loopClasses()
			annotation = annotateImageClass()
			detectObjectsInOneImageForOneClass
			add anno


simplest case: call processImage() standalone, image and model in, annotation out
	needs a wrapper to open the image and model, and to write the annotaion to a file

manual results in a new starting model
train results in a new ending model

detect assume finished model, write annotations

iannotation = 'training.json'
oannotation - 'annotate.json'

we might want to make the images and training.json files readonly
'''



'''
presets out
scoring


usage:
	input saved model
	manually choose starting model 
	process one image: image in, desired outcome in, model in, classifier and bbox list out, score out
	score one image with one model
		inputs: image, model, desired outcome
		outputs: actual outcome, score
	train model for one image
	train model for multiple images
		inputs: folder full of images, desired outcomes
		

	run one image repeatedly, thru all possible models, scoring each, return best model for the image
	run multiple images repeatedly

one object per image
	classification, classifier
	localization, bbox
multiple objects per image
	detection, list of classifier and bbox for each object in the image

clustering
threshhold
segmentation
edge detection, outline, mask, bbox 
computer vision, same as object detection



usage:

realtime onboard awacs, function called for every frame




object_list 
# called in realtime from every awacs capture
# called once for cones and once for vehicles
# one model for each class


def detect(img, model):
	# write objects.json per image
	return objects

def train(fname, model):
	# write model.json per folder
	#oblistDesired = read object list
	oblistActual = detectObjects()
	score = score(oblistDesired, oblistActual)
	if score < low_score:
		best_model = model
	return best_model

def score(oblist1, oblist2):
	#compare lists	
	#do we want low score or high score?
	#0 is equal
	#absolute value of score, the lower the better
	#compare each item in the list
	#classifer, box
	#box: l,t,r,b
	#diff: l,t,r,b
	#squared diff: l,t,r,b
	#score = average of the 4 squared diffs
	#"mean squared error"
	#what about missing objects in actual list?
	#what about extra objects in actual list?
	score = 12
	return score
'''	

