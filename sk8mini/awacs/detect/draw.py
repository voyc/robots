''' 
draw.py - library of drawing functions
'''

import cv2
import numpy as np
import copy
import math
import colorsys
import os

import model as mod

def createImage(shape=(600,600,3), color=(255,255,255)):
	image = np.zeros(shape, np.uint8)
	image[:,:] = color
	return image

def createMask(shape=(600,600), color=(0,0,0)):
	image = np.zeros(shape, np.uint8)
	return image

bgr_color_stack = {
	'white':    (255,255,255),
	'black':    (  0,  0,  0),
	'red':      (  0,  0,255),
	'blue':     (255,  0,  0),
	'green':    (  0,255,  0),
	'yellow':   (  0,255,255),
	'magenta':  (255,  0,255),
	'cyan':     (255,255,  0),
	'pink':     (128,128,255),
	'ltblue':   (255,128,128),
	'ltgreen':  (128,255,128),
	'ltyellow': (128,255,255),
	'ltcyan':   (255,255,128),
	'ltmagenta':(255,128,255),
	'brown':    (  0,128,128) 
}

default_options = {
	"background": "image",   # image, black, white
	"format": "annotation",   # annotation, map
	"thickness_normal": 2,
	"thickness_selected": 4,
	"title": '',
}

def annotateImage(image, labels, model, options={}, selected=-1):
	options = default_options | options

	if options['background'] == 'image':
		imgOut = copy.deepcopy(image)
	elif options['background'] == 'white':
		imgOut = np.full(image.shape, 255, dtype = np.uint8)  # black background
	elif options['background'] == 'black':
		imgOut = np.full(image.shape, 0, dtype = np.uint8)  # black background

	ndx = 0
	for label in labels:
		cls, x, y, w, h, hdg, scr = label
		modcls = mod.getModcls(model,cls)

		rect = ((x,y), (w,h), hdg)
		box = np.intp(cv2.boxPoints(rect))
		color = bgr_color_stack[modcls['acolor']]
		radius = modcls['radius']
		thickness = options['thickness_selected'] if ndx == selected else options['thickness_normal']

		if options['format'] == 'annotation':
			imgOut = cv2.drawContours(imgOut, [box], 0, color, thickness)
		elif options['format'] == 'map':
			imgOut = cv2.circle(imgOut, (x,y), radius, color, -1)

		if modcls['arrow'] == 1 and hdg >= 0:
			drawArrow(imgOut, (x,y), hdg, w+h, color)

		if options['title']:
			imgOut = titleImage(imgOut, options['title'])
		ndx += 1
	return imgOut

def titleImage(img, title):
	imgOut = copy.deepcopy(img)
	cv2.putText(imgOut, title, (20,40), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0), 2)
	return imgOut

def showImage(*args, windowname='show', fps=0, grid=[1,1], screen=(1910,900)):
	img = stack(*args, grid=grid, screen=screen)
	cv2.imshow(windowname, img)
	delay = 0
	if fps:
		delay = round(1000/fps)
	key = cv2.waitKey(delay)
	#cv2.destroyAllWindows()
	return key

def drawArrow(img, ctr, angle, length, color):
	x = ctr[0]
	y = ctr[1]
	θ = (angle-90) * 3.14 / 180.0   # angle in degrees to radians
	x2 = int(x + (length/2) * math.cos(θ))
	y2 = int(y + (length/2) * math.sin(θ))
	x3 = int(x - (length/2) * math.cos(θ))
	y3 = int(y - (length/2) * math.sin(θ))
	img = cv2.arrowedLine(img, (x3,y3), (x2,y2), color, 2, 0, 0, 0.2)

def stack(*args, screen=(1910,900), grid=[1,1]):
	#  input images can be list or separate args, make it a list
	imglist = []
	if type(args[0]) is list:
		imglist = args[0]
	else:
		for img in args:
			imglist.append(img)

	# convert depth if necessary
	aray = []
	ndx = 0
	for img in imglist:
		if len(img.shape) < 3:
			gray = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
			aray.append(gray)
		else:
			aray.append(img)
		ndx += 1

	# input dimensions
	cols, rows = grid 
	screenwd, screenht = screen
	wd, ht = aray[0].shape[0:2]	

	# adjust dimensions
	adjwd, adjht = wd, ht
	if screenwd < (cols * wd):
		adjwd = int(screenwd / cols)
		adjht = int((adjwd/wd) * ht)
	if screenht < (rows * adjht):
		adjht = int(screenht / rows)
		adjwd = int((adjht/ht) * wd)

	# shrink the images if necessary
	if adjwd > 0:
		bray = []
		for img in aray:
			resized = cv2.resize(img, dsize=[adjwd,adjht])
			bray.append(resized)
	else:
		bray = aray	

	# put images in 2D array of rows and cols
	rcray = [ [0]*cols for i in range(rows)]
	ndx = 0
	for img in bray:
		nrow = math.floor(ndx / cols)
		ncol = ndx - (nrow * cols)
		rcray[nrow][ncol] = img
		ndx += 1

	# fill out the bottom row with blanks
	while ndx < cols * rows:
		ncol = ndx - (nrow * cols)
		rcray[nrow][ncol] = np.zeros((rcray[0][0].shape), np.uint8)
		ndx += 1

	# stack columns and rows
	horzimgs = []
	for row in rcray:
		rowimg = np.hstack( row)
		horzimgs.append(rowimg)
	imgOut = np.vstack(horzimgs)

	return imgOut	

def HSVfromBGR(b,g,r):
	# https://math.stackexchange.com/questions/556341/rgb-to-hsv-color-conversion-algorithm
	r /= 255
	g /= 255
	b /= 255
	maxc = max(r, g, b)
	minc = min(r, g, b)
	v = maxc
	if minc == maxc:
	    return 0.0, 0.0, v
	s = (maxc-minc) / maxc
	rc = (maxc-r) / (maxc-minc)
	gc = (maxc-g) / (maxc-minc)
	bc = (maxc-b) / (maxc-minc)
	if r == maxc:
	    h = 0.0+bc-gc
	elif g == maxc:
	    h = 2.0+rc-bc
	else:
	    h = 4.0+gc-rc
	h = (h/6.0) % 1.0
	h *= 180	
	s *= 255
	v *= 255
	return h,s,v 

def BGRfromHSV(h,s,v):
	h /= 180
	s /= 255
	v /= 255
	(r,g,b) = colorsys.hsv_to_rgb(h,s,v)
	r *= 255
	g *= 255
	b *= 255
	return b,g,r

def overlayTransparent(background, foregrond):
	# make working copies
	composite = copy.deepcopy(background)
	overlay   = copy.deepcopy(foreground)
	
	# both of these images must have an alpha channel
	composite = cv2.cvtColor(composite, cv2.COLOR_BGR2BGRA)
	overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2BGRA)
	
	# in overlay, make black transparent
	tmp = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY) 
	_, alpha = cv2.threshold(tmp,20, 255, cv2.THRESH_BINARY) 
	b, g, r, a = cv2.split(overlay) 
	rgba = [b, g, r, alpha] 
	overlay = cv2.merge(rgba, 4) 
	  
	# normalize alpha channels from 0-255 to 0-1
	alpha_composite = composite[:,:,3] / 255.0
	alpha_overlay = overlay[:,:,3] / 255.0
	
	# calc beta, so that alpha + beta = 1
	beta_composite = 1 - alpha_composite
	beta_overlay = 1 - alpha_overlay
	
	# in composite, set adjusted colors, one pixel at a time
	for color in range(0, 3):
		composite[:,:,color] = \
			alpha_overlay * overlay[:,:,color] + \
			alpha_composite * composite[:,:,color] * beta_overlay
	
	# set adjusted alpha
	composite[:,:,3] = (1 - beta_overlay * beta_composite)
	
	# denormalize back to 0-255
	composite[:,:,3] = composite[:,:,3] * 255
	
	# all images must have same shape for display
	composite = cv2.cvtColor(composite, cv2.COLOR_BGRA2BGR) 
	return composite
	
