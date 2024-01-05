'''
detect.py - object detection library
using image processing rather than a neural net
originally taken from tello murtaza
See robots/autonomy/hippoc.py and https://www.youtube.com/watch?v=aJsPsY1hIhop
'''

import numpy as np
import cv2

def detectObjectsMurtaza(img, settings):
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


def detectObjects(img,model,cls):
	def inRange( a, lower, upper):  # comparing np arrays
		return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

	mod = model[cls]

	# algo 1 hsv
	sp = mod['spec']
	lower = np.array([sp[0]['value'], sp[2]['value'], sp[4]['value']])
	upper = np.array([sp[1]['value'], sp[3]['value'], sp[5]['value']])
	imgMask = cv2.inRange(img,lower,upper)

	contours, _ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

	#qualify by size
	sz = mod['size']
	lowerSize = np.array([sz[0][0], sz[1][0]])
	upperSize = np.array([sz[0][1], sz[1][1]])

	labels = []
	for cnt in contours:

		if False:
			rect = cv2.minAreaRect(cnt) 
			size = rect[1]
		else:
			bbox = cv2.boundingRect(cnt)
			x, y, w, h = bbox
			size = np.array([w,h])
		
		if inRange(size, lowerSize, upperSize):
			row = [cls,x,y,w,h,0]
			labels.append(row)

	#print(f'contours found: {len(contours)}, qualified by size: {len(labels)}')
	return labels

