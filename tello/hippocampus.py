'''
hippocamapus.py - object detection by color

Two public methods:
	processFrame
		detectObjects - visual cortex, pareital lobe, occipital lobe, Brodmann area
		buildMap - hippocampus, retrosplenial cortex
	drawUI


todo

add home as inverted copy of initial pad
fit arena to rotated rect
superimpose map onto frame
underimpose frame under map
match frame to map

calc pxlpermm from pad, cones, or camera height

'''
import cv2 as cv
import numpy as np
from datetime import datetime
import logging
import os
import copy
import colorsys

class Pt:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def tuple(self):
		return (int(self.x),int(self.y))
	
	def __str__(self):
		return f'({self.x},{self.y})'

def averageTwoPoints(pt1, pt2):
	data = [pt1.tuple(), pt2.tuple()]
	average = [sum(x)/len(x) for x in zip(*data)]
	xc,yc = average

	#x2= pt2.x
	#y2= pt2.y
	#xc = pt1.x + ((x2 - pt1.x) / 2)
	#yc = pt1.y + ((y2 - pt1.y) / 2)
	return Pt(xc,yc)

def triangulateTwoPoints(ptleft, ptright):
	# length of hypotenuse
	lenx = abs(ptright.x - ptleft.x)
	leny = abs(ptright.y - ptleft.y)
	hypotenuse = np.sqrt(lenx**2 + leny**2)

	# point of right angle
	ptr = Pt(ptleft.x, ptright.y)

	quadrant = quadrantPoints(ptleft,ptright)

	# angle of the hypotenuse to the vertical axis
	# see https://www.geogebra.org/classic/h6pgbftp  # sketch of quadrant upper left
	if quadrant == 'upper right' or quadrant == 'lower left':
		oa = leny/lenx if (lenx != 0) else 0 # tangent of angle = opposite over adjacent 
	else:
		oa = lenx/leny if (leny != 0) else 0 # tangent of angle = opposite over adjacent 
	radians = np.arctan(oa)
	degrs = np.degrees(radians)

	if quadrant == 'lower right':
		degrs += 90
	elif quadrant == 'lower left':
		degrs += 180
	elif quadrant == 'upper left':
		degrs += 270
	return degrs, hypotenuse, ptr
	
def quadrantAngle(angle):
	quadrant = ''
	if angle >= 0 and angle < 90:
		quadrant = 'upper right'
	elif angle >= 90 and angle < 180:
		quadrant = 'lower right'
	elif angle >= 180 and angle < 270:
		quadrant = 'lower left'
	elif angle >= 270 and angle <= 360:
		quadrant = 'upper left'
	return quadrant

def quadrantPoints(ptleft, ptright):
	quadrant = ''
	if ptleft.x < ptright.x and ptleft.y < ptright.y:
		quadrant = 'upper right'
	elif ptleft.x < ptright.x and ptleft.y > ptright.y:
		quadrant = 'upper left'
	elif ptleft.x > ptright.x and ptleft.y < ptright.y:
		quadrant = 'lower right'
	elif ptleft.x > ptright.x and ptleft.y > ptright.y:
		quadrant = 'lower left'
	return quadrant


def calcLine(c,r,a):
	angle = np.radians(a)
	lenh = r # length of hypotenuse
	#                                soh cah toa
	leno = round(np.sin(angle) * lenh) # opposite: sine(angle = opposite/hypotenuse)
	lena = round(np.cos(angle) * lenh) # adjacent: cos(angle = adjacent/hypotenuse)

	x,y = c

	x1 = x + leno
	y1 = y - lena
	x2 = x - leno
	y2 = y + lena

	return (x1,y1), (x2,y2) 

def drawPolygon(img, ptarray, factor=1, color=(255,0,0), linewidth=1):	
	a = np.multiply(ptarray,factor)
	a = a.astype(int)
	for i in range(0,len(a)):
		j = i+1 if i < len(a)-1 else 0
		cv.line(img, tuple(a[i]), tuple(a[j]), color, linewidth)

class Bbox:
	def __init__(self, l,t,w,h):
		self.l = l
		self.t = t
		self.w = w
		self.h = h
		self.calc()

	def calc(self):
		self.r = self.l + self.w
		self.b = self.t + self.h
		self.center = Pt(self.l+round(self.w/2,6), self.t+round(self.h/2,6))
		self.diameter = (self.w+self.h)/2
		self.radius = self.diameter/2

	def intersects(self, r2):
		if self.l > r2.l and self.l < r2.r \
		or self.r > r2.l and self.r < r2.r \
		or self.t > r2.t and self.t < r2.b \
		or self.b > r2.t and self.b < r2.b: 
			return True
		else:
			return False

	def expand(self, padding):
		self.l -= padding
		self.t -= padding
		self.w += (padding*2)
		self.h += (padding*2)
		self.calc()

	def __str__(self):
		return f'({self.l},{self.t},{self.w},{self.h})'

class DetectedObject:
	def __init__(self, cls, bbox, inputunits=False):
		self.cls = cls
		self.bbox = bbox
		
class Pad:
	def __init__(self,padl,padr):
		self.padl = padl
		self.padr = padr
		self.calc()

	def calc(self):
		self.center = averageTwoPoints(self.padl.bbox.center, self.padr.bbox.center)
		self.angle,self.radius,self.pt3 = triangulateTwoPoints(self.padl.bbox.center, self.padr.bbox.center)
		# [angle, radius]  = similar to a vector in that it indicates direction and distance
		# [leny, lenx]  = a slope, rise over run
		# [lenx, leny] = a vector, [2,4] means move 2 mm to the left and 4 mm up

class Arena:
	def __init__(self,bbox):
		self.bbox = bbox
'''
rise straight up until the pad is in view
copy pad to home
continue to rise until first cone spotted
when the pad and one cone are in view:
	copy pad to home
	save distance and angle between home and cone
(note: we can theoretically assume the drone does not rotate, and therefore, 
		one cone is enough to plot the home location)
continue to rise, now centered on the cone
when the second cone is found
	now you can begin to move the pad, 
	because with two cones, you can triangulate the home position
when the third cone is found
	make the final map
even though we are going straight up, we need to navigate to hover

beginner project:
	from takeoff position, find pad, cones, rotated arena
	navigate to hover:
		each frame should be identical
		assume the drone position is dead center in the frame
		with each frame
			build a frame map
			compare to mission map
			orient the frame map, by angle and distance
			convert angle and distance to a tello command 
			execute the command

orientation for beginners
	assume the drone does not yaw
	let all objects be stationary and in-view in every frame
		this allows you to use arena center and angle only to compare frame to frame

an orientation is a vector: distance and angle

arena is a (center, wh, angle), can be drawn as rectangle or elipse

goal 1: hover over pad
goal 2: hover over arena
goal 3: fly around the perimeter - more difficult orientation?
goal 4: perfect landing on pad (add dot if necessary)

cheat: use two cones as starting gate, or four

'''
class Map:
	def __init__(self, pad, cones, arena):
		self.pad = pad
		self.cones = cones
		self.arena = arena

class Hippocampus:
	def __init__(self, ui=True, saveTrain=True):
		self.ui = ui
		self.saveTrain = saveTrain

		# object classification codes
		self.clsCone = 0
		self.clsPadl = 1
		self.clsPadr = 2

		# settings
		self.clsdebug = -1 # self.clsCone  # -1
		self.debugPad = True

		self.datalineheight = 22
		self.datalinemargin = 5

		self.useNeuralNet = False

		self.save_train_nth = 10
		self.save_post_nth = 60

		self.outfolderbase = '/home/john/sk8/images/'

		self.pad_radius = 70     # pad is 14 cm square
		self.cone_radius = 40    # cone diameter is 8 cm
		self.cone_radius_range = 0.40
		self.arena_padding = 80  # turning radius. keep sk8 in the arena.

		self.arena_margin = 40
		self.barmax = {
			'hue_min'  : 255,
			'hue_max'  : 255,
			'sat_min'  : 255,
			'sat_max'  : 255,
			'val_min'  : 255,
			'val_max'  : 255,
			'canny_lo' : 255,
			'canny_hi' : 255
		}

		self.cone_settings = {
			'hue_min'  : 0,
			'hue_max'  : 8,
			'sat_min'  : 107,
			'sat_max'  : 255,
			'val_min'  : 89,
			'val_max'  : 255,
			'canny_lo' : 82,
			'canny_hi' : 127,  # Canny recommended a upper:lower ratio between 2:1 and 3:1.
			'cls'      : self.clsCone,
		}
		self.padl_settings = {
			'hue_min'  : 26,
			'hue_max'  : 53,
			'sat_min'  : 107,
			'sat_max'  : 255,
			'val_min'  : 104,
			'val_max'  : 245,
			'canny_lo' : 82,
			'canny_hi' : 127,
			'cls'      : self.clsPadl
		}
		self.padr_settings = {
			'hue_min'  : 130, #122,
			'hue_max'  : 170, #166,
			'sat_min'  : 45,  #37,
			'sat_max'  : 118, #96,
			'val_min'  : 115, #71,
			'val_max'  : 255, #192, #146,
			'canny_lo' : 82,
			'canny_hi' : 127,
			'cls'      : self.clsPadr
		}

		# variables
		self.framenum = 0        # tello    nexus    pixel     
		self.frameWidth  = 0     #     ?      720      720
		self.frameHeight = 0     #     ?      540      405
		self.frameDepth  = 0     #     ?        3        3

		self.frameMap = False
		self.baseMap = False
		self.ovec = False  # orienting vector

		self.imgColor = False
		self.imgPost = False
		self.posts = {}
		self.debugImages = []
		self.outfolder = ''
	
		# aircraft altitude is measured in multiple ways
		#    agl - above ground level
		#    msl - mean sea level, based on 19-year averages
		#    barometric pressure, varies depending on the weather

		# baro reported by the tello is assumed to be MSL in meters to two decimal places
		#    a typical value before flying is 322.32
		#    the elevation of Chiang Mai is 310 meters

		# before takeoff, the camera is 20mm above the pad
		# all of our internal calculations are in mm

		# check to see that telemetry data and height commands are equivalent
		# design a mission to test
		# write debug msgs to log showing comparison and differences

		# we use a technique of 
		# we compare apparent size to known size of 
		# we are taking downward-facing photos of pad and cones
		# objects with known size

		self.baro_agl = 0    # reported by tello barometer
		self.camera_agl = 0  # computed by apparent size of pad in image
		self.pxlpermm = 0    # computed as function of agl

	def openUI(self):
		if self.ui:
			if self.clsdebug == self.clsCone:
				self.openSettings(self.cone_settings, 'cone')
			elif self.clsdebug == self.clsPadl:
				self.openSettings(self.padl_settings, 'padl')
			elif self.clsdebug == self.clsPadr:
				self.openSettings(self.padr_settings, 'padr')

	def closeUI(self):
		if self.ui:
			cv.destroyAllWindows()

	def post(self,key,value):
		self.posts[key] = value
	
	def drawPosts(self):
		linenum = 1
		ssave = ''
		for k in self.posts.keys():
			v = self.posts[k]
			s = f'{k}={v}'
			pt = (self.datalinemargin, self.datalineheight * linenum)
			cv.putText(self.imgPost, s, pt, cv.FONT_HERSHEY_SIMPLEX,.7,(0,0,0), 1)
			linenum += 1
			ssave += s + ';'
		if self.framenum % self.save_post_nth == 0:
			logging.debug(ssave)
	
	def openSettings(self, settings, name):
		def empty(a): # passed to trackbar
			pass
	
		window_name = f'{name} Settings'
		cv.namedWindow( window_name)
		cv.resizeWindow( window_name,640,240)
		for setting in settings:
			if setting != 'cls':
				cv.createTrackbar(setting, window_name, settings[setting], self.barmax[setting],empty)
	
	def readSettings(self, settings, name):
		window_name = f'{name} Settings'
		for setting in settings:
			if setting != 'cls':
				settings[setting] = cv.getTrackbarPos(setting, window_name)

		# create the debugging color image
		# debug hsv range
		self.imgColor = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image

		hl,hu,sl,su,vl,vu,_,_,_ = settings.values()
		print(hl)	
		hl /= 179
		hu /= 179
		sl /= 255
		su /= 255
		vl /= 255
		vu /= 255

		rl,gl,bl = colorsys.hsv_to_rgb(hl,sl,vl)
		ru,gu,bu = colorsys.hsv_to_rgb(hu,su,vu)

		rl *= 255
		ru *= 255
		gl *= 255
		gu *= 255
		bl *= 255
		vu *= 255
		

		colormin = bl,gl,rl
		colormax = bu,gu,ru
		#colormin = [settings['hue_min'],settings['sat_min'],settings['val_min']]
		#colormax = [settings['hue_max'],settings['sat_max'],settings['val_max']]

		#imgColor.fill(255)
		for y in range(0, int(self.frameHeight/2)):
			for x in range(self.frameWidth):
				self.imgColor[y,x] = colormin   # [255,255,255]
		for y in range(int(self.frameHeight/2), self.frameHeight):
			for x in range(self.frameWidth):
				self.imgColor[y,x] = colormax   # [128,128,128]
	
	def xstackImages(self,scale,imgArray):
		rows = len(imgArray)
		cols = len(imgArray[0])
		rowsAvailable = isinstance(imgArray[0], list)
		width = imgArray[0][0].shape[1]
		height = imgArray[0][0].shape[0]
		if rowsAvailable:
			for x in range ( 0, rows):
				for y in range(0, cols):
					if imgArray[x][y].shape[:2] == imgArray[0][0].shape [:2]:
						imgArray[x][y] = cv.resize(imgArray[x][y], (0, 0), None, scale, scale)
					else:
						imgArray[x][y] = cv.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale, scale)
					if len(imgArray[x][y].shape) == 2: imgArray[x][y]= cv.cvtColor( imgArray[x][y], cv.COLOR_GRAY2BGR)
			imageBlank = np.zeros((height, width, 3), np.uint8)
			hor = [imageBlank]*rows
			hor_con = [imageBlank]*rows
			for x in range(0, rows):
				hor[x] = np.hstack(imgArray[x])
			ver = np.vstack(hor)
		else:
			for x in range(0, rows):
				if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
					imgArray[x] = cv.resize(imgArray[x], (0, 0), None, scale, scale)
				else:
					imgArray[x] = cv.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None,scale, scale)
				if len(imgArray[x].shape) == 2: imgArray[x] = cv.cvtColor(imgArray[x], cv.COLOR_GRAY2BGR)
			hor= np.hstack(imgArray)
			ver = hor
		return ver
	
	def stackImages(self,scale,imgArray):
		# imgArray is a tuple of lists
		rows = len(imgArray)     # number of lists in the tuple
		cols = len(imgArray[0])  # number of images in the first list

		height,width,depth = imgArray[0][0].shape

		for x in range ( 0, rows):
			for y in range(0, cols):
				# scale images down to fit on screen
				imgArray[x][y] = cv.resize(imgArray[x][y], (0, 0), None, scale, scale)

				# imshow() requires BGR, so convert grayscale images to BGR
				if len(imgArray[x][y].shape) == 2: 
					imgArray[x][y]= cv.cvtColor( imgArray[x][y], cv.COLOR_GRAY2BGR)

		imageBlank = np.zeros((height, width, 3), np.uint8)  # shouldn't this be scaled?
		hor = [imageBlank]*rows  # initialize a blank image space
		for x in range(0, rows):
			hor[x] = np.hstack(imgArray[x])
		ver = np.vstack(hor)

		return ver
	
	def drawMap(self, map, img):
		
		pad = map.pad if map.pad else false
		cones = map.cones if map.cones else False
		arena = map.arena if map.arena else False

		# draw arena
		l = int(round(arena.bbox.l * self.pxlpermm))
		t = int(round(arena.bbox.t * self.pxlpermm))
		r = int(round(arena.bbox.r * self.pxlpermm))
		b = int(round(arena.bbox.b * self.pxlpermm))
		cv.rectangle(img, (l,t), (r,b), (127,0,0), 1)
	
		# draw cones
		r = int(round(self.cone_radius * self.pxlpermm))
		for cone in cones:
			#x = int(round(arena.bbox.center.x + (obj.bbox.center.x * self.frameWidth)))
			#y = int(round(arena.bbox.center.y + (obj.bbox.center.y * self.frameHeight)))
			x = int(round(cone.bbox.center.x * self.pxlpermm))
			y = int(round(cone.bbox.center.y * self.pxlpermm))
			cv.circle(img,(x,y),r,(0,0,255),1)
	
		# draw pad
		if pad:
			if self.debugPad: # draw the halves
				l = int(round(pad.padl.bbox.l * self.pxlpermm))
				t = int(round(pad.padl.bbox.t * self.pxlpermm))
				r = int(round(pad.padl.bbox.r * self.pxlpermm))
				b = int(round(pad.padl.bbox.b * self.pxlpermm))
				cv.rectangle(img, (l,t), (r,b), (0,255,255), 1) # bgr yellow, left

				l = int(round(pad.padr.bbox.l * self.pxlpermm))
				t = int(round(pad.padr.bbox.t * self.pxlpermm))
				r = int(round(pad.padr.bbox.r * self.pxlpermm))
				b = int(round(pad.padr.bbox.b * self.pxlpermm))
				cv.rectangle(img, (l,t), (r,b), (255,0,255), 1) # bgr purple, right
			
				drawPolygon(img, [pad.padl.bbox.center.tuple(), pad.padr.bbox.center.tuple(), pad.pt3.tuple()], self.pxlpermm)
	
			#  outer perimeter
			r = round(self.pad_radius * self.pxlpermm)
			x = round(pad.center.x * self.pxlpermm)
			y = round(pad.center.y * self.pxlpermm)
			cv.circle(img,(x,y),r,(0,0,0),1)

			# axis with arrow
			pt1, pt2 = calcLine((x,y), r, pad.angle)
			cv.line(img,pt1,pt2,(0,0,0),1)  # center axis
			cv.circle(img,pt1,3,(0,0,0),3)   # arrow pointing forward

	def drawUI(self, img):
		if self.ui and self.frameMap and self.baseMap:
			# map
			imgMap = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
			imgMap.fill(255)  # made white
			self.drawMap(self.frameMap, imgMap)
		
			# frame overlaid with oriented map
			imgFinal = img.copy()
			self.drawMap(self.frameMap, imgFinal)

			self.drawMap(self.baseMap, imgFinal)

			# hippocampus internal data calculations posted by programmer
			self.imgPost = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
			self.imgPost.fill(255)
			self.drawPosts()
	
			imgTuple = ([imgMap,self.imgPost,imgFinal],)
			if self.clsdebug >= 0:
				imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = self.debugImages
				imgHsv= cv.cvtColor( imgHsv, cv.COLOR_HSV2BGR)
				imgTuple = ([self.imgPost,self.imgColor,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal])
			stack = self.stackImages(0.8,imgTuple)
			cv.imshow('Image Processing', stack)

	#
	# end UI section, begin image processing section
	#

	def detectObjectsNN(self,img):
		pass

	def detectObjectsCV(self,img):
		objects = []
		self.detectContours(img, self.cone_settings, objects)
		self.detectContours(img, self.padl_settings, objects)
		self.detectContours(img, self.padr_settings, objects)
		return objects

	def detectContours(self,img,settings,objects):
		# mask based on hsv ranges
		lower = np.array([settings['hue_min'],settings['sat_min'],settings['val_min']])
		upper = np.array([settings['hue_max'],settings['sat_max'],settings['val_max']])
		imgHsv = cv.cvtColor(img,cv.COLOR_BGR2HSV)
		imgMask = cv.inRange(imgHsv,lower,upper)
		imgMasked = cv.bitwise_and(img,img, mask=imgMask)
	
		imgBlur = cv.GaussianBlur(imgMasked, (7, 7), 1)
		imgGray = cv.cvtColor(imgBlur, cv.COLOR_BGR2GRAY)
	
		# canny: edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
		imgCanny = cv.Canny(imgGray, settings['canny_lo'], settings['canny_hi'])
	
		# dilate: thicken the line
		kernel = np.ones((5, 5))
		imgDilate = cv.dilate(imgCanny, kernel, iterations=1)

		# get a data array of polygons, one contour boundary for each object
		contours, _ = cv.findContours(imgDilate, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
		if self.clsdebug == settings['cls']:
			self.debugImages = [imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate]

		# get bounding box for each contour
		for contour in contours:
			area = cv.contourArea(contour)
			perimeter = cv.arcLength(contour, True)
			polygon = cv.approxPolyDP(contour, 0.02 * perimeter, True)
			l,t,w,h = cv.boundingRect(polygon)

			tl = round(l/self.frameWidth, 6)
			tt = round(t/self.frameHeight, 6)
			tw = round(w/self.frameWidth, 6)
			th = round(h/self.frameHeight, 6)

			bbox = Bbox(tl,tt,tw,th)
			obj = DetectedObject(settings['cls'], bbox)
			objects.append(obj)
		return

	def findPad(self, objects):
		padla = []
		for obj in objects:
			if obj.cls == self.clsPadl:
				padla.append(obj)
		padra = []
		for obj in objects:
			if obj.cls == self.clsPadr:
				padra.append(obj)

		self.post('num padla', len(padla))
		self.post('num padra', len(padra))
		if len(padla) <= 0 or len(padra) <= 0:
			return False

		# if multiples, choose the one with the largest radius 
		objpadl = padla[0]
		for obj in padla:
			if obj.bbox.radius > objpadl.bbox.radius:
				objpadl = obj
		objpadr = padra[0]
		for obj in padra:
			if obj.bbox.radius > objpadr.bbox.radius:
				objpadr = obj

		# go back and scrub objects list
		for obj in objects:
			if obj.cls == self.clsPadl and obj is not objpadl:
				objects.remove(obj)
			if obj.cls == self.clsPadr and obj is not objpadr:
				objects.remove(obj)

		# padr and padl are expected to intersect
		# if angle is straight up, they could be adjacent, but this is unlikely
		if not objpadl.bbox.intersects( objpadr.bbox):
			logging.debug('pad halves do not intersect')

		# from pct to pxl
		padl = copy.deepcopy(objpadl)
		padl.bbox.l *= self.frameWidth
		padl.bbox.t *= self.frameHeight
		padl.bbox.w *= self.frameWidth 
		padl.bbox.h *= self.frameHeight 
		padl.bbox.calc()

		padr = copy.deepcopy(objpadr)
		padr.bbox.l *= self.frameWidth
		padr.bbox.t *= self.frameHeight
		padr.bbox.w *= self.frameWidth 
		padr.bbox.h *= self.frameHeight 
		padr.bbox.calc()

		# calc pad radius in pixels
		_,pxlPadRadius,_ = triangulateTwoPoints(padl.bbox.center, padr.bbox.center)

		# conversion factor pxl per mm
		# nb: conversion factor implies an agl
		self.pxlpermm = pxlPadRadius / self.pad_radius
		self.post('conversion pxl per mm', self.pxlpermm)
		self.post('mm frame width', self.frameWidth / self.pxlpermm)
		self.post('mm frame height', self.frameHeight/ self.pxlpermm)
		# 170cm w : 1700 mm w

		# from pxl to mm
		padl.bbox.l /= self.pxlpermm
		padl.bbox.t /= self.pxlpermm
		padl.bbox.w /= self.pxlpermm
		padl.bbox.h /= self.pxlpermm
		padl.bbox.calc()

		padr.bbox.l /= self.pxlpermm
		padr.bbox.t /= self.pxlpermm
		padr.bbox.w /= self.pxlpermm
		padr.bbox.h /= self.pxlpermm
		padr.bbox.calc()

		# create pad object in mm
		pad = Pad(padl,padr)
		self.post('padl center', padl.bbox.center)
		self.post('padr center', padr.bbox.center)
		self.post('quadrant', quadrantPoints(padl.bbox.center, padr.bbox.center))
		self.post('pad center', pad.center)
		self.post('pad angle' , pad.angle)
		self.post('pad radius', pad.radius)

		return pad

	def findCones(self, objects):
		# choose only correctly sized objects, scrub object list
		cones = []

		radmin = self.cone_radius - (self.cone_radius_range*self.cone_radius)
		radmax = self.cone_radius + (self.cone_radius_range*self.cone_radius)

		numconeobjs = 0
		for obj in objects:
			if obj.cls == self.clsCone:
				numconeobjs += 1

				# from pct to pxl
				cone = copy.deepcopy(obj)
				cone.bbox.l *= self.frameWidth
				cone.bbox.t *= self.frameHeight
				cone.bbox.w *= self.frameWidth 
				cone.bbox.h *= self.frameHeight 

				# from pxl to mm
				cone.bbox.l /= self.pxlpermm
				cone.bbox.t /= self.pxlpermm
				cone.bbox.w /= self.pxlpermm
				cone.bbox.h /= self.pxlpermm
				cone.bbox.calc()
				if cone.bbox.radius > radmin and cone.bbox.radius < radmax:
					cones.append(cone)
				#else:
				#	objects.remove(obj)

		self.post('cones found', numconeobjs)
		self.post('cones accepted', len(cones))
		return cones
		

	def findArenaRot(self, cones):
		pta = []
		for cone in cones:	
			pt = cone.bbox.center.tuple()
			pta.append(pt)
		rect = cv.minAreaRect(np.array(pta)) # center, (w,h), angle as -90 to 0
		box = cv.boxPoints(rect)   # 4 points
		box = np.int0(box)          # convert to int to pass to cv.rectangle
		arenarot = ArenaRot(rect)
		return arenarot
 	
	def findArena(self, cones):
		# non-rotated arena, bbox from cones
		l = self.frameWidth
		r = 0
		t = self.frameHeight
		b = 0
		bbox = Bbox(l,t,r-l,b-t)
		for cone in cones:
			x = cone.bbox.center.x
			y = cone.bbox.center.y
			if x < l:
				l = x
			if x > r:
				r = x
			if y < t:
				t = y
			if y > b:
				b = y

		bbox = Bbox(l,t,r-l,b-t)
		bbox.expand(self.arena_padding)
		arena  = Arena(bbox)
		return arena

	def matchMap(data):
		pass
	
	def saveTrainingData(self,img,objects):
		if self.saveTrain and self.framenum % self.save_train_nth == 0:
			ht = str(self.camera_agl*10) # remove decimal point
			fname = f'{self.outfolder}/sk8_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}_ht_{ht}'
			imgname = f'{fname}.jpg'
			txtname = f'{fname}.txt'
			cv.imwrite(imgname,img)
			f = open(txtname, 'a')

			for obj in objects:
				f.write(f"{obj.cls} {obj.bbox.t} {obj.bbox.l} {obj.bbox.w} {obj.bbox.h}\n")
			f.close()

	def start(self):
		logging.info('hippocampus starting')
		self.openUI()

		# create daily log folder
		self.outfolder = f'{self.outfolderbase}{datetime.now().strftime("%Y%m%d")}/'
		if not os.path.exists(self.outfolder):
			os.makedirs(self.outfolder)

	def stop(self):
		logging.info('hippocampus stopping')
		self.closeUI()

	def detectObjects(self,img):
		if self.useNeuralNet:
			return self.detectObjectsNN(img)
		else:
			return self.detectObjectsCV(img)

	def buildMap(self,objects):
		pad = self.findPad(objects)
		if not pad:
			return False

		cones = self.findCones(objects)
		arena = self.findArena(cones)
		map = Map(pad, cones, arena)
		return map
	
	def processFrame(self,img,baro_agl):
		self.baro_agl = baro_agl
		self.framenum += 1
		self.frameHeight,self.frameWidth,self.frameDepth = img.shape
		self.post('pxl frame width', self.frameWidth)
		self.post('pxl frame height', self.frameHeight)

		# get settings from trackbars
		if self.ui:
			if self.clsdebug == self.clsCone:
				self.readSettings( self.cone_settings, 'cone')
			elif self.clsdebug == self.clsPadl:
				self.readSettings( self.padl_settings, 'padl')
			elif self.clsdebug == self.clsPadr:
				self.readSettings( self.padr_settings, 'padr')

		# detect objects - unit: percent of frame
		self.objects = self.detectObjects(img)
		self.post('objects found',len(self.objects))

		# build map
		self.frameMap = self.buildMap(self.objects)
		if not self.baseMap:
			self.baseMap = self.frameMap
		else:
			# orient frame to map
			angle,radius,_ = triangulateTwoPoints( self.baseMap.pad.center, self.frameMap.pad.center)
			# use this to navigate angle and radius, to counteract drift
			# assume stable agl and no yaw, so angle and radius refers to drift
			# in this case, drawing basemap over framemap results only in offset, not rotation or scale

			
			ovec = np.array(self.frameMap.pad.center.tuple()) - np.array(self.baseMap.pad.center.tuple())
			diffx,diffy = ovec

			cmd = ''
			if diffx > 100:
				cmd = 'left 20'
			elif diffx < -100:
				cmd = 'right 20'
			elif diffy > 100:
				cmd = 'forward 20'
			elif diffx < -100:
				cmd = 'back 20'
			#jsendCommand(cmd)
			print(cmd)

		#	sendCommand('sdk?')

			# compare pad angle and radius between basemap and framemap
			# use this to reorient frame to map
			# rotate basemap and draw on top of frame image
			# rotate framemap and frameimg and draw underneath basemap


		# save image and objects for mission debriefing and neural net training
		self.saveTrainingData(img, self.objects)

		if self.ui:
			self.drawUI(img)

	def parseFilenameForAgl(self, fname):
		agl = int(fname.split('_agl_')[1].split('.')[0])
		return agl

if __name__ == '__main__':
	def startLogging(filename):
		logging.basicConfig(
			format='%(asctime)s %(module)s %(levelname)s %(message)s', 
			filename=filename, 
			level=logging.DEBUG) # 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)  # console does not get DEBUG level
		logging.getLogger('').addHandler(console)
		logging.info('logging configured')

	logfolder = '/home/john/sk8/logs/'
	fname = f'{logfolder}/sk8_{datetime.now().strftime("%Y%m%d")}.log' # daily logfile
	startLogging(fname)

	imgfolder = '../imageprocessing/images/cones/train/'
	imgfile = 'helipad_and_3_cones.jpg'
	imgfile = 'IMG_20200623_174503.jpg'
	imgfile = 'sk8_angle_210_agl_1000.jpg'
	imgfile = 'sk8_1_meter_agl_1000.jpg'
	imgfile = 'sk8_2_meter_agl_2000.jpg'
	imgfile = 'sk8_angle_45_agl_1000.jpg'   # angle  37, upper right
	imgfile = 'sk8_angle_135_agl_1000.jpg'  # angle 126, lower right
	imgfile = 'sk8_angle_210_agl_1000.jpg'  # angle 217, lower left
	imgfile = 'sk8_angle_290_agl_1000.jpg'  # angle 290, upper left

	imgfile1 = 'sk8_angle_45_agl_1000.jpg'   # angle  37, upper right
	imgfile2 = 'sk8_angle_135_agl_1000.jpg'  # angle 126, lower right

	hippocampus = Hippocampus(True, True)
	hippocampus.start()

	ht = hippocampus.parseFilenameForAgl(imgfile1)
	img = cv.imread(imgfolder+imgfile1, cv.IMREAD_UNCHANGED)
	hippocampus.processFrame(img, ht)

	while True:
		ht = hippocampus.parseFilenameForAgl(imgfile2)
		img = cv.imread(imgfolder+imgfile2, cv.IMREAD_UNCHANGED)
		hippocampus.processFrame(img, ht)
		hippocampus.drawUI(img)
		if cv.waitKey(1) & 0xFF == ord('q'):
			break

	hippocampus.stop()

