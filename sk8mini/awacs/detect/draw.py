''' 
draw.py - library of drawing functions
'''

import cv2
import numpy as np
import copy
import math
import colorsys
import os

def createImage(shape=(600,600,3), color=(255,255,255)):
	image = np.zeros(shape, np.uint8)
	image[:,:] = color
	return image

def createMask(shape=(600,600), color=(0,0,0)):
	image = np.zeros(shape, np.uint8)
	return image

default_options = {
	"format": "overlay",   # overlay, map, sbs
	"thickness_normal": 2,
	"thickness_selected": 4,
	"title": '',
	"color":"red"
}

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

color_stack = [
	(  0,  0,255), # red
	(255,  0,  0), # blue
	(  0,255,  0), # green
	(  0,255,255), # yellow
	(255,  0,255), # magenta
	(255,255,  0), # cyan
	(128,128,255), # pink
	(255,128,128), # ltblue
	(128,255,128), # ltgreen
	(128,255,255), # ltyellow
	(255,255,128), # ltcyan
	(255,128,255)  # ltmagenta
]

radius_stack = [ 11, 12, 12, 12, 3, 35, 8, 35 ]

def drawImage(image, labels, options={}, selected=-1):
	options = default_options | options
	imgformat = options['format']

	if imgformat in ['overlay', 'sbs']:
		imgOut = imgLay = drawOverlay(image, labels, options, selected)
	if imgformat in ['map' , 'sbs']:
		imgOut = imgMap = drawMap(image, labels, options, selected)

	if imgformat == 'sbs':
		imgOut = np.hstack((image, imgLay, imgMap))

	if options['title']:
		imgOut = titleImage(imgOut, options['title'])
	return imgOut

def drawOverlay(image, labels, options, selected):
	imgOut = copy.deepcopy(image)
	ndx = 0
	for label in labels:
		cls, x, y, w, h, hdg, scr = label
		color = color_stack[cls-1]
		color = bgr_color_stack[options['colors'][cls]]
		thickness = options['thickness_normal']
		if ndx == selected:
			thickness = options['thickness_selected']
		rect = ((x,y), (w,h), hdg)
		box = cv2.boxPoints(rect)
		box = np.intp(box)
		imgOut = cv2.drawContours(imgOut, [box], 0, color, thickness)

		if cls == 2:
			drawLine(imgOut, (x,y), hdg, w)
			#cv2.putText(imgOut, f'{hdg}', box[1], cv2.FONT_HERSHEY_PLAIN, 2, color)
		ndx += 1
	return imgOut

def drawMap(image, labels, options, selected):
	imgOut = np.full(image.shape, 255, dtype = np.uint8) 
	for label in labels:
		cls, x, y, w, h, hdg, scr = label
		color = color_stack[cls-1]
		radius = radius_stack[cls-1]
		cv2.circle(imgOut, (x,y), radius, color, -1)

		if cls == 3:
			drawLine(imgOut, (x,y), hdg, h)
	return imgOut

def titleImage(img, title):
	imgOut = copy.deepcopy(img)
	cv2.putText(imgOut, title, (20,40), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0), 2)
	return imgOut

def showImage(*args, windowname='show', fps=0, grid=[1,1], screen=(1910,900)):
	cols,rows = grid
	img = stack(*args, cols=cols, rows=rows, screen=screen)
	cv2.imshow(windowname, img)
	delay = 0
	if fps:
		delay = round(1000/fps)
	key = cv2.waitKey(delay)
	#cv2.destroyAllWindows()
	return key

def drawLine(img, ctr, angle, length=100):
	x = ctr[0]
	y = ctr[1]
	θ = (angle-90) * 3.14 / 180.0   # angle in degrees to radians
	x2 = int(x + (length/2) * math.cos(θ))
	y2 = int(y + (length/2) * math.sin(θ))
	x3 = int(x - (length/2) * math.cos(θ))
	y3 = int(y - (length/2) * math.sin(θ))
	cv2.arrowedLine(img, (x3,y3), (x2,y2), (0,255,0), 2, 0, 0, 0.2)

def drawVehicle(img, vehicle):
	box = vehicle[0]	
	ctr = vehicle[1]	
	angle = vehicle[2]	
	cv2.drawContours(img, [box], 0, (0,0,255),1)
	drawLine(img, ctr, angle, 50)

def stack(*args, screen=(1910,900), cols=1, rows=1):
	#  input can be list or separate args
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

	# check width
	screenwd = screen[0]
	screenht = screen[1]
	wd = aray[0].shape[0]	
	ht = aray[0].shape[1]	
	num = len(aray)
	numrows = 1
	numcols = num

	if cols > 0:
		numcols = cols
		numrows = math.ceil(num/numcols)
	else:
		# go to two rows if necessary
		if screenwd < (num * wd):
			numrows = 2
			numcols = math.ceil(num / 2)

	# next, shrink the images if necessary
	newwd = newht = 0
	if screenwd < (numcols * wd):
		newwd = int(screenwd / numcols)
		newht = int((newwd/wd) * ht)
	elif screenht < (numrows * ht):
		newht = int(screenht / numrows)
		newwd = int((newht/ht) * wd)
	
	if newwd > 0:
		bray = []
		for img in aray:
			resized = cv2.resize(img, dsize=[newwd,newht])
			bray.append(resized)
	else:
		bray = aray	

	# stack cols
	ar = [ [0]*numcols for i in range(numrows)]
	ndx = 0
	for img in bray:
		nrow = math.floor(ndx / numcols)
		ncol = ndx - (nrow * numcols)
		ar[nrow][ncol] = img
		ndx += 1

	# add extra blank if odd
	if not hasattr(ar[numrows-1][numcols-1], '__len__'):
		blank = np.zeros((ar[0][0].shape), np.uint8)
		ar[numrows-1][numcols-1] = blank

	# stack rows
	img = []
	for row in ar:
		rowimg = np.hstack( row)
		img.append(rowimg)
	if numrows ==  1:
		imgOut = img[0]
	else:
		imgOut = np.vstack(img)

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
	
