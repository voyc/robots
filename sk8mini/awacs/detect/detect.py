'''
objdet_imgproc.py - object detection by image processing

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
'''
import numpy as np
import cv2
from datetime import datetime
import sys
import json


eyesheight = 2000

cone_radius = 40 # cone diameter is 8 cm

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

model = {
	'cone': {
		'name'     : 'cone',
		'cls'    : 1,
		'hue_min'  : 0,
		'hue_max'  : 127,
		'sat_min'  : 107,
		'sat_max'  : 255,
		'val_min'  : 89,
		'val_max'  : 255,
		'canny_lo' : 82,
		'canny_hi' : 127,
		'r_min'  :  10,
		'r_max'  : 900,
	},
	'wheel': {
		'name'     : 'wheel',
		'cls'    : 2,
		'hue_min'  : 0,
		'hue_max'  : 14,
		'sat_min'  : 107,
		'sat_max'  : 255,
		'val_min'  : 89,
		'val_max'  : 255,
		'canny_lo' : 82,
		'canny_hi' : 127,
		'r_min'  :  10,
		'r_max'  : 900,
	}
}

annotate = []

# global variables
frameWidth = 640
frameHeight = 480
pxlpermm = 0

datalineheight = 22
datalinemargin = 5

#
#
# manual model settings
#
#

def empty(a): # passed to trackbar
	pass

def openSettings(settings):
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

#def navigate():
#	# draw text nav recommendation
#	deadZone=100
#	if (cx < int(frameWidth/2)-deadZone):
#		cv2.putText(img, " GO LEFT " , (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
#	elif (cx > int(frameWidth / 2) + deadZone):
#		cv2.putText(img, " GO RIGHT ", (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
#	elif (cy < int(frameHeight / 2) - deadZone):
#		cv2.putText(img, " GO UP ", (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
#	elif (cy > int(frameHeight / 2) + deadZone):
#		cv2.putText(img, " GO DOWN ", (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1,(0, 0, 255), 3)

def drawMap(arena, cones, pad, img):
	# draw arena
	pl = round(arena['pcx'] + (arena['l'] * pxlpermm))
	pt = round(arena['pcy'] + (arena['t'] * pxlpermm))
	pr = round(arena['pcx'] + (arena['r'] * pxlpermm))
	pb = round(arena['pcy'] + (arena['b'] * pxlpermm))
	cv2.rectangle(img, (pl,pt), (pr,pb), (127,0,0), 1)

	# draw cones
	r = round(cone_radius * pxlpermm)
	for cone in cones:
		px = round(arena['pcx'] + (cone[0] * pxlpermm))
		py = round(arena['pcy'] + (cone[1] * pxlpermm))
		cv2.circle(img,(px,py),r,(0,0,255),1)

	# draw pad
	r = round(pad_radius * pxlpermm)
	px = round(arena['pcx'] + (pad['c'][0] * pxlpermm))
	py = round(arena['pcy'] + (pad['c'][1] * pxlpermm))
	cv2.circle(img,(px,py),r,(255,0,255),1)

	a = pad['a']

	cv2.circle(img,(px,py),r,(255,0,255),1)

	pt1, pt2,s = calcLine((px,py), r, a)
	cv2.line(img,pt1,pt2,(255,0,255),1)
	cv2.circle(img,pt1,3,(255,0,255),1)

def calcLine(c,r,a):
	h = np.radians(a)
	#a = np.tan(a)  # angle in degrees to slope as y/x ratio
	lenc = r
	lenb = round(np.sin(h) * lenc) # opposite
	lena = round(np.cos(h) * lenc) # adjacent
	x = c[0]
	y = c[1]
	x1 = x + lena
	y1 = y + lenb
	x2 = x - lena
	y2 = y - lenb
	a = round(a)
	s = f'{a} {lena} {lenb}'
	return (x1,y1), (x2,y2), s 

def getObjectData(cones, padr, padl, frameWidth, frameHeight):
	coneclass = 0
	padrclass  = 1
	padlclass  = 2
	data = []
	for contour in cones:
		obj = calcDataFromContour(coneclass, contour, frameWidth, frameHeight)		
		data.append(obj)

	for contour in padr:
		obj = calcDataFromContour(padrclass, contour, frameWidth, frameHeight)		
		data.append(obj)
		
	for contour in padl:
		obj = calcDataFromContour(padlclass, contour, frameWidth, frameHeight)		
		data.append(obj)
	return data

def calcDataFromContour(cls, contour, frameWidth, frameHeight):
	# calc area, center, radius in pixels
	area = cv2.contourArea(contour)
	peri = cv2.arcLength(contour, True)
	approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
	x, y, w, h = cv2.boundingRect(approx)
	cx = int(x + (w / 2))
	cy = int(y + (h / 2))
	r = max(w,h)/2
	#r = math.sqrt(a/np.pi())

	# rotated rectangle, for pad
	rr = cv2.minAreaRect(contour) # (cx,cy), (w,h), angle

	# training data: percentage of image
	tx = round(x/frameWidth, 6)
	ty = round(y/frameHeight, 6)
	tw = round(w/frameWidth, 6)
	th = round(h/frameHeight, 6)

	obj = {
		'px': x ,  # pixels bounding box
		'py': y ,
		'pw': w ,
		'ph': h ,
		'pr': r ,
		'pcx':cx,
		'pcy':cy,
		'tx':tx,  # training data, pct of frame, bounding box
		'ty':ty,
		'tw':tw,
		'th':th,
		'rr':rr,
		'cl':cls  # class 0:cone, 1:padr, 2:padl
	}
	return obj

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

def matchMap(data):
	pass

def buildMap(data):
	global pxlpermm

	# conversion factors depend on camera height
	pxlpermmat1m = 0.5964285714
	pxlpermmat2m = 0.3071428571
	if eyesheight == 1000:
		pxlpermm = pxlpermmat1m
	elif eyesheight == 2000:
		pxlpermm = pxlpermmat2m

	# find arena boundary and center in pixels
	pxlarena = {
		'l':frameWidth,
		'r':0,
		't':frameHeight,
		'b':0,
	}
	for row in data:
		if row['cl'] == 0:
			pcx = row['pcx']
			pcy = row['pcy']
			if pcx < pxlarena['l']:
				pxlarena['l'] = pcx
			if pcx > pxlarena['r']:
				pxlarena['r'] = pcx
			if pcy < pxlarena['t']:
				pxlarena['t'] = pcy
			if pcy > pxlarena['b']:
				pxlarena['b'] = pcy
	a = arena_padding * pxlpermm
	pxlarena['l'] -= a
	pxlarena['t'] -= a
	pxlarena['r'] += a
	pxlarena['b'] += a
	pxlarena['cx'] = pxlarena['l'] + ((pxlarena['r'] - pxlarena['l']) / 2)
	pxlarena['cy'] = pxlarena['t'] + ((pxlarena['b'] - pxlarena['t']) / 2)
	
	# convert arena boundary and center to mm
	arena = {}
	arena['cx'] = 0  # arena center is null island
	arena['cy'] = 0
	arena['pcx'] = pxlarena['cx']
	arena['pcy'] = pxlarena['cy']
	arena['w'] = (pxlarena['r'] - pxlarena['l']) / pxlpermm
	arena['h'] = (pxlarena['b'] - pxlarena['t']) / pxlpermm
	arena['r'] = (arena['cx'] + (arena['w'] / 2)) #/ pxlpermm
	arena['l'] = (arena['cx'] - (arena['w'] / 2)) #/ pxlpermm
	arena['b'] = (arena['cy'] + (arena['h'] / 2)) #/ pxlpermm
	arena['t'] = (arena['cy'] - (arena['h'] / 2)) #/ pxlpermm

	# convert centers to mm
	cones = []
	pad = {}
	for row in data:
		cx = (row['pcx'] - pxlarena['cx']) / pxlpermm
		cy = (row['pcy'] - pxlarena['cy']) / pxlpermm
		if row['cl'] == 0:
			cones.append((cx,cy))
		elif row['cl'] == 1:
			pad['rc'] = ((cx,cy))
			pad['ra'] = row['rr'][2]
			pad['rrr'] = row['rr']
		elif row['cl'] == 2:
			pad['lc'] = ((cx,cy))
			pad['la'] = row['rr'][2]
			pad['lrr'] = row['rr']

	# combine pad r and l center
	pad['c'] = averageTwoPoints(pad['lc'], pad['rc'])

	# pad angle per contour rotated rect
	pad['a2'] = (pad['la'] + pad['ra']) / 2

	# pad angle per trig between the r and l centers
	x1,y1 = pad['lc']
	x2,y2 = pad['rc']
	lenx = x2 - x1
	leny = y2 - y1
	oh = leny/lenx
	angle = np.arctan(oh)
	degrs = np.degrees(angle)
	pad['a'] = degrs - 90 # we want angle to the y-axis instead of to the x-axis
	return arena, cones, pad

def averageTwoPoints(ptr, ptl):
	cxl,cyl = ptl
	cxr,cyr = ptr
	cxc = cxl + ((cxr - cxl) / 2)
	cyc = cyl + ((cyr - cyl) / 2)
	center = (cxc,cyc)
	return center
	
#def saveTrainingData(data,img):
#	fname = f'{outfolder}/sk8_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}'
#	imgname = f'{fname}.jpg'
#	txtname = f'{fname}.txt'
#	cv2.imwrite(imgname,img)
#	f = open(txtname, 'a')
#	for row in data:
#		f.write(f"{row['cl']} {row['tx']} {row['ty']} {row['tw']} {row['th']}\n")
#	f.close()

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
'''	

def detectCones(img, conemodel):
	return detect(img, conemodel)
	
def detectWheels(img, wheelmodel):
	return detect(img, wheelmodel)
	
def detectSk8(img, sk8model):
	object_list = detectWheels(img, wheelmodel)
	sk8object = findSk8(object_list)

	#given 4 wheels and 1 donut
	#we can get the center, heading and turning angle of the sk8mini

	#now we have two sources of turning angle, the second being the deck tilt by imu

	return sk8object
	
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
	
#def detectObjects(image, model): 
#	return object_list

#
#
#  model management
#
#
# dict = json.loads(s)       # load string to dict
# string = json.dumps(dict)  # dump dict to string, with pretty print

# dict = object
# x = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))

def trainModel():
	return model

def printModel(model):
	print(json.dumps(model, indent=4))
	print(f'model contains {len(model)} classifiers')
	for m in model:
		print(f'{model[m]["cls"]} {m}')

def writeModel(model, fname):
	with open(fname, 'w') as f:
		f.write(json.dumps(model, indent=4))

def readModel(fname):
	with open(fname, 'r') as f:
		x = json.load(f)
	return x

#
#
# annotate management
#
#

def readAnnotate():
	return

def writeAnnotate(annotate, fname):
	with open(fname, 'w') as f:
		for a in annotate:
			f.write( f'{a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]}, {a[5]}, {a[6]}, {a[7]}\n')

def printAnnotate(annotate):
	for a in annotate:
		print( f'{a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]}, {a[5]}, {a[6]}, {a[7]}')

def writeUsage():
	print('usage:')
	print('if --train = True, omodel is output')
	print('if not --train, oannotate is output per image')
	print('if output filename is not specified, the input filename is overwritten')
	print('one model for the folder')
	print('one annotation for each image file')
	print('if oimage is specified, the input image is rewritten in the output folder')
	print('any one of seven image types may be output')


def main():
	# string parameters  --param=value
	ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
	ofolder = ''
	iimage = 'all'
	oimage = 'none'
	imodel = 'model.json'
	omodel = ''
	iannotate = ''
	oannotate = ''
	cls = 'all'

	# boolean parameters, --param, present or not
	ismanual = False
	istrain = False
	isverbose = False

	# read params from command line
	for i in range(1, len(sys.argv)):
		if i == len(sys.argv):
			iimage = sys.argv(len(sys.argv)) 
		elif sys.argv[i].__contains__('='):
			param, value = sys.argv[i].split('=' )
			if param == '--ifolder':
				ifolder = value
			if param == '--ofolder':
				ofolder = value
			if param == '--iimage':
				iimage = value
			if param == '--oimage':
				oimage = value
			if param == '--imodel':
				imodel = value
			if param == '--omodel':
				omodel = value
			if param == '--iannotate':
				iannotate = value
			if param == '--oannotate':
				oannotate= value
			if param == '--cls':
				cls = value
		else:
			if sys.argv[i] == '--manual':
				ismanual = True
			if sys.argv[i] == '--train':
				istrain = True
			if sys.argv[i] == '--verbose':
				isverbose = True
			if sys.argv[i] == '--help':
				writeUsage()
				quit()

	# set defaults for missing params
	if ofolder == '':
		ofolder = ifolder
	if oimage == '':
		oimage = iimage
	if omodel == '':
		omodel = imodel
	if iannotate == '':
		iannotate = iimage.replace('.jpg', '_trained.csv' )
	if oannotate == '':
		oannotate = iannotate

	# print input parameters
	if isverbose:
		print(f'ifolder: {ifolder}')
		print(f'ofolder: {ofolder}')
		print(f'iimage: {iimage}')
		print(f'oimage: {oimage}')
		print(f'imodel: {imodel}')
		print(f'omodel: {omodel}')
		print(f'iannotate: {iannotate}')
		print(f'oannotate: {oannotate}')
		print(f'manual: {ismanual}')
		print(f'train: {istrain}')

	# read first image
	if iimage != 'all':
		imgInput = cv2.imread(ifolder+iimage, cv2.IMREAD_UNCHANGED)
		if isverbose: 
			print(f'image shape: {imgInput.shape}')
		frameHeight,frameWidth,frameDepth = imgInput.shape

	# read model
	model = readModel(ifolder+imodel)
	if isverbose:
		printModel(model)

	# read annotation 
	#annotate = readAnnote(ifolder+iannotate)
	#if isverbose:
	#	printAnnotate(annotate)

	# for each class in the model
	#for m in model:
	#	processClass(imgInput, model, cls)

	if ismanual:
		openSettings(model[cls])

	while True:
		if ismanual:
			readSettings( model[cls])

		annotate, images = detectObjects(imgInput, model[cls])
	
		# show the images
		if ismanual:
			imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate, imgEdged = images
			stack = stackImages(0.7,([imgInput,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgEdged]))
			cv2.imshow('Image Processing', stack)
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break
		else:
			break

	cv2.destroyAllWindows()

	if ismanual or istrain:
		if isverbose:
			print('writing model')
		writeModel(model, ofolder+omodel)
		printModel(model) 

	if isverbose:
		print('writing annotate')
	writeAnnotate(annotate, ofolder+oannotate)
	printAnnotate(annotate)


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
