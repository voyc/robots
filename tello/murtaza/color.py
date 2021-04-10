#Color Detection
import cv2
import numpy as np

onetime = False 
showWork = True
showsettings = True 

frameWidth = 640
frameHeight = 480
#cap = cv2.VideoCapture(1)
#cap.set(3, frameWidth)
#cap.set(4, frameHeight)

imgfolder = '../../imageprocessing/images/cones/train/'
coneimg = 'IMG_20200623_174503.jpg'
coneimg = 'helipad_and_3_cones.jpg'
#coneimg = '../../images/cones/train/IMG_20200623_174509.jpg'
#coneimg = '../../images/cones/train/IMG_20200623_174519.jpg'

deadZone=100

def empty(a):
	pass

# cone settings
#cone_window_name = 'Settings'
#cone_hue_min  = 0    # hsv ranges
#cone_hue_max  = 8
#cone_sat_min  = 107
#cone_sat_max  = 255
#cone_val_min  = 89
#cone_val_max  = 255
#cone_canny_lo = 82   # canny edge detection algorithm
#cone_canny_hi = 127  # Canny recommended a upper:lower ratio between 2:1 and 3:1.
#cone_area_min = 324   # min area (size) of cone contour
#cone_area_max = 30000 # not used except in trackbar

barmax = {
	'hue_min'  : 179,
	'hue_max'  : 179,
	'sat_min'  : 255,
	'sat_max'  : 255,
	'val_min'  : 255,
	'val_max'  : 255,
	'canny_lo' : 255,
	'canny_hi' : 255,
	'area_min' : 3000
}

cone_settings = {
	'hue_min'  : 0,    # hsv ranges
	'hue_max'  : 8,
	'sat_min'  : 107,
	'sat_max'  : 255,
	'val_min'  : 89,
	'val_max'  : 255,
	'canny_lo' : 82,   # canny edge detection algorithm
	'canny_hi' : 127,  # Canny recommended a upper:lower ratio between 2:1 and 3:1.
	'area_min' : 324,   # min area (size) of cone contour
}

lzr_settings = {
	'hue_min'  : 0,    # hsv ranges
	'hue_max'  : 8,
	'sat_min'  : 107,
	'sat_max'  : 255,
	'val_min'  : 89,
	'val_max'  : 255,
	'canny_lo' : 82,   # canny edge detection algorithm
	'canny_hi' : 127,  # Canny recommended a upper:lower ratio between 2:1 and 3:1.
	'area_min' : 324,   # min area (size) of cone contour
}

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

def drawMap(contours, img):
	# initialize the arena
	arena = {'l':frameWidth, 't':frameHeight, 'r':0, 'b':0}

	# draw each contour in the array
	for contour in contours:
		# draw the contour
		#cv2.drawMap(img, contour, -1, (255, 0, 255), 7)

		# calculations
		area = cv2.contourArea(contour)
		peri = cv2.arcLength(contour, True)
		approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
		x, y, w, h = cv2.boundingRect(approx)
		cx = int(x + (w / 2))
		cy = int(y + (h / 2))

		# draw bounding box 	
		cv2.rectangle(img, (x , y ), (x + w , y + h ), (0, 255, 0), 5)

		# draw info texts: num points, area, x:y point
		cv2.putText(img, "Points: " + str(len(approx)), (x + w + 20, y + 20), cv2.FONT_HERSHEY_COMPLEX, .7,
					(0, 255, 0), 2)
		cv2.putText(img, "Area: " + str(int(area)), (x + w + 20, y + 45), cv2.FONT_HERSHEY_COMPLEX, 0.7,
					(0, 255, 0), 2)
		cv2.putText(img, " " + str(int(x))+ " "+str(int(y)), (x - 20, y- 45), cv2.FONT_HERSHEY_COMPLEX, 0.7,
					(0, 255, 0), 2)

		# draw text nav recommendation
		if (cx < int(frameWidth/2)-deadZone):
			cv2.putText(img, " GO LEFT " , (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
		elif (cx > int(frameWidth / 2) + deadZone):
			cv2.putText(img, " GO RIGHT ", (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
		elif (cy < int(frameHeight / 2) - deadZone):
			cv2.putText(img, " GO UP ", (20, 50), cv2.FONT_HERSHEY_COMPLEX,1,(0, 0, 255), 3)
		elif (cy > int(frameHeight / 2) + deadZone):
			cv2.putText(img, " GO DOWN ", (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1,(0, 0, 255), 3)

		# draw line from center point to contour
		cv2.line(img, (int(frameWidth/2),int(frameHeight/2)), (cx,cy),
				 (0, 0, 255), 3)

		# enlarge the arena to include each contour
		if x < arena['l']:
			arena['l'] = x
		if y < arena['t']:
			arena['t'] = y
		if (x+w) > arena['r']:
			arena['r'] = x+w
		if (y+h) > arena['b']:
			arena['b'] = y+h

		# draw a black circle around the cone
		cone_radius = 20
		cv2.circle(img,(cx,cy),cone_radius,(0,0,0),1)

	# draw the arena
	arena_margin = 10
	arena['l'] -= arena_margin;
	arena['t'] -= arena_margin;
	arena['r'] += arena_margin;
	arena['b'] += arena_margin;
	cv2.rectangle(img, (arena['l'], arena['t'] ), (arena['r'], arena['b'] ), (0, 0, 0), 1)

	# draw vertical meridians
	cv2.line(img,(int(frameWidth/2)-deadZone,0),(int(frameWidth/2)-deadZone,frameHeight),(255,255,0),3)
	cv2.line(img,(int(frameWidth/2)+deadZone,0),(int(frameWidth/2)+deadZone,frameHeight),(255,255,0),3)

	# draw center circle
	cv2.circle(img,(int(frameWidth/2),int(frameHeight/2)),5,(0,0,255),5)

	# draw horizontal parallels
	cv2.line(img, (0,int(frameHeight / 2) - deadZone), (frameWidth,int(frameHeight / 2) - deadZone), (255, 255, 0), 3)
	cv2.line(img, (0, int(frameHeight / 2) + deadZone), (frameWidth, int(frameHeight / 2) + deadZone), (255, 255, 0), 3)


def getContours(img):
	''' 
	contours - an array of shapes. 
		Each shape is an array of points making up the edge of the shape.
	hierarchy - irrelevant.  There are no cones within cones.	
	'''
	contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
	numcontours = len(contours)

	# throw away the small ones
	for contour in contours:
		area = cv2.contourArea(contour)
		areaMin = cone_settings['area_min']
		if area < areaMin:
			contours.remove(contour)

	if onetime:
		print(f'num contours: {len(contours)}, discarded: {numcontours - len(contours)}')
	return contours


# main begins here

if showsettings:
	openSettings(cone_settings, 'Cone')
	openSettings(lzr_settings, 'LZR')

while True:

	# img: the original photo or frame
	#_, img = cap.read()
	img = cv2.imread(imgfolder+coneimg, cv2.IMREAD_UNCHANGED)
	if onetime:
		print(f'image shape (height,width,depth): {img.shape}')
		# nexus: 720 x 540 x 3
		# pixel: 720 x 405 x 3
		# tello: ?
	frameHeight,frameWidth,frameDepth = img.shape

	# get settings from trackbars
	if showsettings:
		readSettings( cone_settings, 'Cone')
		readSettings( cone_settings, 'LZR')

	# mask based on hsv ranges
	lower = np.array([cone_settings['hue_min'],cone_settings['sat_min'],cone_settings['val_min']])
	upper = np.array([cone_settings['hue_max'],cone_settings['sat_max'],cone_settings['val_max']])
	imgHsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
	imgMask = cv2.inRange(imgHsv,lower,upper)
	imgMasked = cv2.bitwise_and(img,img, mask=imgMask)

	imgBlur = cv2.GaussianBlur(imgMasked, (7, 7), 1)
	imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_BGR2GRAY)

	# canny: edge detection
	imgCanny = cv2.Canny(imgGray, cone_settings['canny_lo'], cone_settings['canny_hi'])

	# dilate: thicken the line
	kernel = np.ones((5, 5))
	imgDilate = cv2.dilate(imgCanny, kernel, iterations=1)

	# get a data array of cone objects
	contours = getContours(imgDilate)

	# map: draw lines and circles and texts
	imgMap = np.zeros((frameHeight, frameWidth, frameDepth), np.uint8) # blank image
	imgMap.fill(255)
	drawMap(contours, imgMap)

	# final: draw map over original photo
	imgFinal = img.copy()
	drawMap(contours, imgFinal)


	# show the images
	stack = stackImages(0.7,([img,imgFinal]))
	if showWork:
		stack = stackImages(0.7,([img,imgHsv,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal]))
	cv2.imshow('img:imgMasked:dilate:contour', stack)

	# break loop and quit
	if cv2.waitKey(1) & 0xFF == ord('q'):
		break
	if onetime:
		break

#cap.release()
cv2.destroyAllWindows()
