'''
testclustering.py - test K-means clustering
'''
import numpy as np
import cv2
import os
import math

# read image
fname = 'photos/20231216-092941/00148.jpg'
imgBgr = cv2.imread(fname, cv2.IMREAD_UNCHANGED)

cv2.:w
imgBgr

o# cluster the pixel intensities
clt = KMeans(n_clusters = args["clusters"])
clt.fit(image)

# mask based on hsv ranges
lower = np.array([23, 114,  57])
upper = np.array([37, 225, 205])
imgMaskYellow = cv2.inRange(imgHsv,lower,upper)

# invert mask
imgInvertedMask = cv2.bitwise_not(imgMaskYellow)

# mask based on gray values
imgMaskBlack = cv2.inRange(imgGray, 10, 50)  # looking for black
imgMaskWhite = cv2.inRange(imgGray, 100, 250)  # looking for white


# make square mask around vehicle
sz = np.array([ 50, 50])
ctr = np.array([323,145])
lt = ctr - sz
rb = ctr + sz
l,t = lt
r,b = rb
color = (255,255,255)
thickness = -1

imgCrop = imgBgr[t:b, l:r]

imgVehicleMask = np.zeros(sz, np.uint8)
imgVehicleMask = cv2.rectangle(imgVehicleMask, lt, rb, color, thickness) 

# remove background
#imgCropInv = cv2.bitwise_not(imgCrop)
#imgMasked = cv2.bitwise_and(imgBgr,imgBgr, mask=imgVehicleMask)
draw.showImage(imgVehicleMask)

# canny edge detection
imgCanny = cv2.Canny(imgCrop, 50, 70)

kernel = np.ones((5, 5))
imgClosed = cv2.morphologyEx(imgCanny, cv2.MORPH_CLOSE, kernel)

showImage(imgCrop, imgCanny, imgClosed)
quit()

# dilate
imgMaskVehicle = cv2.dilate(imgCanny, kernel, iterations=3)

showImage(imgMaskVehicle)

contours, _ = cv2.findContours(imgMaskVehicle, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


for cnt in contours:
	rect = cv2.minAreaRect(cnt)
	box = cv2.boxPoints(rect)
	box = np.intp(box)

	#qualify by size
	w = rect[1][0]
	h = rect[1][1]
	if w<25 or h<25:
		continue

	#print(fname)
	#print(rect)
	#print(cv2.boundingRect(cnt))
	#print(cv2.minEnclosingCircle(cnt))
    

	ctr = rect[0]
	ctr = np.intp(ctr)
	angle = rect[2]
	#print(f'ctr:{ctr}, angle:{angle}')

	vehicle = (box, ctr, angle)
	print(ctr)
	drawVehicle(imgBgr, vehicle)


showImage(imgBgr)


'''
		
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

'''

