'color.py - object detection by color'
import cv2
import numpy as np
from datetime import datetime

# global constants
debugOnetime = True 
debugOnetime = False 
debugCones = False
debugLzr = False
debugLzl = False


saventhframe = 10
#cap = cv2.VideoCapture(1)
#cap.set(3, frameWidth)
#cap.set(4, frameHeight)

imgfolder = '../../imageprocessing/images/cones/train/'
coneimg = 'helipad_and_3_cones.jpg'
coneimg = 'IMG_20200623_174503.jpg'
coneimg = 'sk8_2_meter.jpg'
coneimg = 'sk8_1_meter.jpg'
eyesheight = 1000

cone_radius = 40 # cone diameter is 8 cm
pad_radius = 70  # pad is 14 cm square
arena_padding = cone_radius * 2  # turning radius. keep sk8 in the arena.
arena_margin = cone_radius

outfolder = '../../imageprocessing/images/cones/new/train/'

barmax = {
	'hue_min'  : 255,
	'hue_max'  : 255,
	'sat_min'  : 255,
	'sat_max'  : 255,
	'val_min'  : 255,
	'val_max'  : 255,
	'canny_lo' : 255,
	'canny_hi' : 255,
	'area_min' : 3000
}

cone_settings = {
	'hue_min'  : 0,
	'hue_max'  : 8,
	'sat_min'  : 107,
	'sat_max'  : 255,
	'val_min'  : 89,
	'val_max'  : 255,
	'canny_lo' : 82,
	'canny_hi' : 127,  # Canny recommended a upper:lower ratio between 2:1 and 3:1.
	'area_min' : 324,  # min area (size) of contour
}

padr_settings = {
	'hue_min'  : 130, #122,
	'hue_max'  : 170, #166,
	'sat_min'  : 45,  #37,
	'sat_max'  : 118, #96,
	'val_min'  : 115, #71,
	'val_max'  : 255, #192, #146,
	'canny_lo' : 82,
	'canny_hi' : 127,
	'area_min' : 324,
}

padl_settings = {
	'hue_min'  : 26,
	'hue_max'  : 53,
	'sat_min'  : 107,
	'sat_max'  : 255,
	'val_min'  : 104,
	'val_max'  : 245,
	'canny_lo' : 82,
	'canny_hi' : 127,
	'area_min' : 324,
}

# global variables
frameWidth = 640
frameHeight = 480
pxlpermm = 0

def empty(a): # passed to trackbar
	pass

def oneprint(s):
	if debugOnetime:
		print(s)

def openSettings( settings, name):
	window_name = f'{name} Settings'
	cv2.namedWindow( window_name)
	cv2.resizeWindow( window_name,640,240)
	for setting in settings:
		cv2.createTrackbar(setting, window_name, settings[setting], barmax[setting],empty)

def readSettings( settings, name):
	window_name = f'{name} Settings'
	for setting in settings:
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

def navigate():
	# draw text nav recommendation
	deadZone=100
	if (cx < int(frameWidth/2)-deadZone):
		cv2.putText(img, " GO LEFT " , (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
	elif (cx > int(frameWidth / 2) + deadZone):
		cv2.putText(img, " GO RIGHT ", (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
	elif (cy < int(frameHeight / 2) - deadZone):
		cv2.putText(img, " GO UP ", (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
	elif (cy > int(frameHeight / 2) + deadZone):
		cv2.putText(img, " GO DOWN ", (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1,(0, 0, 255), 3)

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

#	r = 200
#	a = 45
#	pt1, pt2, s = calcLine((px,py), r, a)
#	cv2.circle(img,pt1,3,(255,0,255),1)
#	cv2.putText(img, s, pt1, cv2.FONT_HERSHEY_COMPLEX, .7, (0,0,0), 1)
#
#	a = 0
#	pt1, pt2, s = calcLine((px,py), r, a)
#	cv2.circle(img,pt1,3,(255,0,255),1)
#	cv2.putText(img, s, pt1, cv2.FONT_HERSHEY_COMPLEX, .7, (0,0,0), 1)
#
#	a = 270
#	pt1, pt2, s = calcLine((px,py), r, a)
#	cv2.circle(img,pt1,3,(255,0,255),1)
#	cv2.putText(img, s, pt1, cv2.FONT_HERSHEY_COMPLEX, .7, (0,0,0), 1)
#
#	a = 180
#	pt1, pt2, s = calcLine((px,py), r, a)
#	cv2.circle(img,pt1,3,(255,0,255),1)
#	cv2.putText(img, s, pt1, cv2.FONT_HERSHEY_COMPLEX, .7, (0,0,0), 1)
#
#	a = 90
#	pt1, pt2, s = calcLine((px,py), r, a)
#	cv2.circle(img,pt1,3,(255,0,255),1)
#	cv2.putText(img, s, pt1, cv2.FONT_HERSHEY_COMPLEX, .7, (0,0,0), 1)
#
#	cv2.circle(img,(px,py),3,(255,0,255),1)

	pt1, pt2,s = calcLine((px,py), r, a)
	cv2.line(img,pt1,pt2,(255,0,255),1)
	cv2.circle(img,pt1,3,(255,0,255),1)
	cv2.putText(img, s, pt1, cv2.FONT_HERSHEY_COMPLEX, .7, (0,0,0), 1)
#
#	a = 180
#	pt1, pt2 = calcLine((px,py), r, a)
#	cv2.line(img,pt1,pt2,(255,0,255),1)
#
#	a = 270
#	pt1, pt2 = calcLine((px,py), r, a)
#	cv2.line(img,pt1,pt2,(255,0,255),1)
#

	#cv2.circle(img,pt2,5,(255,0,255),1)

	#cv2.putText(img, str(a), (px,py), cv2.FONT_HERSHEY_COMPLEX, .7, (0,0,0), 1)

#	box = cv2.boxPoints(pad['rrr'])
#	box = np.int0(box)
#	cv2.drawContours(img,[box],0,(255,0,255),1)
#
#	box = cv2.boxPoints(pad['lrr'])
#	box = np.int0(box)
#	cv2.drawContours(img,[box],0,(0,255,255),1)

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

#def calcLine(c,r,a):
#	a = np.tan(a)  # angle in degrees to slope as y/x ratio
#
#	# start with center point
#	x = c[0]
#	y = c[1]
#
#	# y = (a*x) + b   # linear equation: y = ax + b
#	b = y - (a*x)     # solve for b, the y-intercept
#
#	# now we know a and b, we can find y for any value of x
#
#	#length^2 = (x2 - x)^2 + (y2 - y)^2    # pythagorean theorem
#	length = r
#
#	# substitute linear equation for y2
#	length^2 = (x2 - x)^2 + (((a * x2) + b) - y)^2
#
#	# solve for x2, two answers
#	length^2 = a^2 + 2*a*x2 + x2^2 + b^2 - y^2 # apply binomial squares formula
#	2*a*x2 + x2^2 = a^2 + b^2 - y^2 - length^2 # switch sides to isolate x2 on the left
#
#
#	# squared binomial
#	(x2 - x)^2 
#	(x2 - x) * (x2 - x)
#	x2*x2 - x2*x - x*x2 + x*x
#	x2^2 + -2*x2*x + x^2
#
#	# squared trinomial incl binomial
#	((a * x2) + b - y)^2
#	(a * x2)^2 + b^2 - y^2
#
#	(a * x2)^2
#	a^2 + 2*a*x2 + x2^2
#
#
#	length^2 = a^2 + 2*a*x2 + x2^2 + b^2 - y^2
#
#
#
#	x = c[0] +100
#	y = round((s * x) + r)
#	pt2 = (x,y)
#
#
#	pt1 = c
#	return pt1, pt2

def xdrawMap(conecontours, padrcontours, padlcontours, img):
	# initialize the arena
#	arena2 = {'l':frameWidth, 't':frameHeight, 'r':0, 'b':0}

	# draw cones
	for contour in conecontours:
		# draw the contour
		#cv2.drawContours(img, contour, -1, (255, 0, 255), 7)

		# calculations
		area = cv2.contourArea(contour)
		peri = cv2.arcLength(contour, True)
		approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
		x, y, w, h = cv2.boundingRect(approx)
		cx = int(x + (w / 2))
		cy = int(y + (h / 2))

		# draw bounding box 	
#		cv2.rectangle(img, (x , y ), (x + w , y + h ), (0, 255, 0), 5)

		# draw info texts: num points, area, x:y point
#		cv2.putText(img, "Points: " + str(len(approx)), (x + w + 20, y + 20), cv2.FONT_HERSHEY_COMPLEX, .7,
#					(0, 255, 0), 2)
#		cv2.putText(img, "Area: " + str(int(area)), (x + w + 20, y + 45), cv2.FONT_HERSHEY_COMPLEX, 0.7,
#					(0, 255, 0), 2)
#		cv2.putText(img, " " + str(int(x))+ " "+str(int(y)), (x - 20, y- 45), cv2.FONT_HERSHEY_COMPLEX, 0.7,
#					(0, 255, 0), 2)

		# draw line from center point to contour
#		cv2.line(img, (int(frameWidth/2),int(frameHeight/2)), (cx,cy),
#				 (0, 0, 255), 3)

		# enlarge the arena2 to include each contour
#		if x < arena2['l']:
#			arena2['l'] = x
#		if y < arena2['t']:
#			arena2['t'] = y
#		if (x+w) > arena2['r']:
#			arena2['r'] = x+w
#		if (y+h) > arena2['b']:
#			arena2['b'] = y+h

		# draw a black circle around the cone
#		cone_radius = 20
#		cv2.circle(img,(cx,cy),cone_radius,(0,0,0),1)

#	for contour in padrcontours:
#		cv2.drawContours(img, contour, -1, (255, 0, 255), 7)
#
#	for contour in padlcontours:
#		cv2.drawContours(img, contour, -1, (255, 0, 255), 7)

	# draw the arena2
#	arena2['l'] -= arena_margin;
#	arena2['t'] -= arena_margin;
#	arena2['r'] += arena_margin;
#	arena2['b'] += arena_margin;
#	cv2.rectangle(img, (arena2['l'], arena2['t'] ), (arena2['r'], arena2['b'] ), (0, 0, 0), 1)

	# draw vertical meridians
	deadZone=100
	cv2.line(img,(int(frameWidth/2)-deadZone,0),(int(frameWidth/2)-deadZone,frameHeight),(255,255,0),3)
	cv2.line(img,(int(frameWidth/2)+deadZone,0),(int(frameWidth/2)+deadZone,frameHeight),(255,255,0),3)

	# draw center circle
	cv2.circle(img,(int(frameWidth/2),int(frameHeight/2)),5,(0,0,255),5)

	# draw horizontal parallels
	cv2.line(img, (0,int(frameHeight / 2) - deadZone), (frameWidth,int(frameHeight / 2) - deadZone), (255, 255, 0), 3)
	cv2.line(img, (0, int(frameHeight / 2) + deadZone), (frameWidth, int(frameHeight / 2) + deadZone), (255, 255, 0), 3)


#def getContours(img):
#	''' 
#	contours - an array of shapes. 
#		Each shape is an array of points making up the edge of the shape.
#	hierarchy - irrelevant.  There are no cones within cones.	
#	'''
#	contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
#	numcontours = len(contours)
#
#	# throw away the small ones
#	#for contour in contours:
#	#	area = cv2.contourArea(contour)
#	#	areaMin = cone_settings['area_min']
#	#	if area < areaMin:
#	#		contours.remove(contour)
#
#	if debugOnetime:
#		print(f'num contours: {len(contours)}, discarded: {numcontours - len(contours)}')
#	return contours

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

def detectObjects(settings):
	# mask based on hsv ranges
	lower = np.array([settings['hue_min'],settings['sat_min'],settings['val_min']])
	upper = np.array([settings['hue_max'],settings['sat_max'],settings['val_max']])
	imgHsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
	imgMask = cv2.inRange(imgHsv,lower,upper)
	imgMasked = cv2.bitwise_and(img,img, mask=imgMask)

	imgBlur = cv2.GaussianBlur(imgMasked, (7, 7), 1)
	imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_BGR2GRAY)

	# canny: edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
	imgCanny = cv2.Canny(imgGray, settings['canny_lo'], settings['canny_hi'])

	# dilate: thicken the line
	kernel = np.ones((5, 5))
	imgDilate = cv2.dilate(imgCanny, kernel, iterations=1)

	# get a data array of polygons, one contour boundary for each object
	contours, _ = cv2.findContours(imgDilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
	return contours, [imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate]

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
	oneprint(f"pad angle {pad['a']} vs {pad['a2']}")
	return arena, cones, pad

def averageTwoPoints(ptr, ptl):
	cxl,cyl = ptl
	cxr,cyr = ptr
	cxc = cxl + ((cxr - cxl) / 2)
	cyc = cyl + ((cyr - cyl) / 2)
	center = (cxc,cyc)
	return center
	
def saveTrainingData(data,img):
	fname = f'{outfolder}/sk8_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}'
	imgname = f'{fname}.jpg'
	txtname = f'{fname}.txt'
	cv2.imwrite(imgname,img)
	f = open(txtname, 'a')
	for row in data:
		f.write(f"{row['cl']} {row['tx']} {row['ty']} {row['tw']} {row['th']}\n")
	f.close()

# main begins here

if debugCones:
	openSettings(cone_settings, 'Cone')
elif debugLzr:
	openSettings(padr_settings, 'LZR')
elif debugLzl:
	openSettings(padl_settings, 'LZL')

framenum = 0
while True:
	framenum += 1

	# img: the original photo or frame
	#_, img = cap.read()
	img = cv2.imread(imgfolder+coneimg, cv2.IMREAD_UNCHANGED)
	oneprint(f'image dimenensions h:{img.shape[0]}, w:{img.shape[1]}, d:{img.shape[2]}')
	# nexus: 720 x 540 x 3
	# pixel: 720 x 405 x 3
	# tello: ?
	frameHeight,frameWidth,frameDepth = img.shape

	# get settings from trackbars
	if debugCones:
		readSettings( cone_settings, 'Cone')
	elif debugLzr:
		readSettings( padr_settings, 'LZR')
	elif debugLzl:
		readSettings( padl_settings, 'LZL')

	conecontours, coneimages = detectObjects(cone_settings)
	padrcontours, padrimages = detectObjects(padr_settings)
	padlcontours, padlimages = detectObjects(padl_settings)

	# reduce the contours to data

	data = getObjectData(conecontours, padrcontours, padlcontours, frameWidth, frameHeight)
	arena, cones, pad = buildMap(data)
	
	if framenum % saventhframe == 0 or debugOnetime:
		saveTrainingData(data, img)

	# map: draw lines and circles and texts
	imgMap = np.zeros((frameHeight, frameWidth, frameDepth), np.uint8) # blank image
	imgMap.fill(255)
	xdrawMap(conecontours, padrcontours, padlcontours, imgMap)
	drawMap(arena, cones, pad, imgMap)

	# final: draw map over original photo
	imgFinal = img.copy()
	xdrawMap(conecontours, padrcontours, padlcontours, imgFinal)

	# show the images
	stack = stackImages(0.7,([img,imgMap,imgFinal]))
	if debugCones:
		imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = coneimages
		stack = stackImages(0.7,([img,imgHsv,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal]))
	elif debugLzr:
		imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = padrimages
		stack = stackImages(0.7,([img,imgHsv,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal]))
	elif debugLzl:
		imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = padlimages
		stack = stackImages(0.7,([img,imgHsv,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal]))
	cv2.imshow('Image Processing', stack)

	# break loop and quit
	if cv2.waitKey(1) & 0xFF == ord('q'):
		break
	if debugOnetime:
		break

#cap.release()
cv2.destroyAllWindows()
