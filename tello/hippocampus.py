'''
hippocamapus.py - class Hippocampus
	spatial analysis, object detection, mapping, orientation
'''
import cv2 as cv
import numpy as np
from datetime import datetime
import time
import logging
import os
import copy
import colorsys
import re
import universal as uni
from sk8math import *
import visualcortex

# calc agl from pxlpermm
agl_k = 1143
def aglFromPxpmm(pxlpermm):
	if pxlpermm <=0:
		return 0
	return int(agl_k/pxlpermm)  # hyperbola equation y=k/x

def drawPolygon(img, ptarray, factor=1, color=(255,0,0), linewidth=1):	
	a = np.multiply(ptarray,factor)
	a = a.astype(int)
	for i in range(0,len(a)):
		j = i+1 if i < len(a)-1 else 0
		cv.line(img, tuple(a[i]), tuple(a[j]), color, linewidth)

class Spot:
	def __init__(self, bbox, pxlpermm):
		self.bbox = bbox
		self.pxlpermm = pxlpermm

class Pad:
	def __init__(self,padl,padr):
		self.padl = padl
		self.padr = padr
		self.spot = False
		self.pxlpermm = False
		self.calc()
		self.purpose = 'frame'  # frame or home
		self.state = ''
		self.half_state = ''

	def getBbox(self):
		l = self.center.x - self.radius
		t = self.center.y - self.radius
		w = self.radius
		h = self.radius
		bx = Bbox(l,t,w,h)
		return bx

	def calc(self):
		if self.padl and self.padr:
			self.center = averageTwoPoints(self.padl.bbox.center, self.padr.bbox.center)
			self.angle,self.radius,self.pt3 = triangulateTwoPoints(self.padl.bbox.center, self.padr.bbox.center)
		else:
			self.center = Pt(0,0)
			self.angle = 0
			self.radius = 0
		self.diameter = self.radius * 2
		# [angle, radius]  = similar to a vector in that it indicates direction and distance
		# [leny, lenx]  = a slope, rise over run
		# [lenx, leny] = a vector, [2,4] means move 2 mm to the left and 4 mm up

class Arena:
	def __init__(self,bbox):
		self.bbox = bbox

class Map:
	def __init__(self, pad, cones, arena, home=False):
		self.pad = pad
		self.cones = cones
		self.arena = arena
		self.home = home 

class Hippocampus:
	def __init__(self, ui=True, save_mission=False):
		self.ui = ui
		self.save_mission = save_mission

		# object classification codes
		self.clsNone = -1
		self.clsCone = 0
		self.clsPadl = 1
		self.clsPadr = 2
		self.clsSpot = 3

		# settings
		self.clsdebug = self.clsCone
		self.debugPad = True 

		self.dialog_width = 480
		self.dialog_height = 480

		self.frameWidth  = 960
		self.frameHeight = 720
		self.frameDepth  = 3

		self.datalineheight = 22
		self.datalinemargin = 5

		self.useNeuralNet = False

		self.frame_nth = 1
		self.post_nth = 0

		self.spot_radius = 8     # spot is 16 mm diameter
		self.spot_offset = 46    # spot center is 46 mm forward of pad center
		self.pad_radius = 70     # pad is 14 cm square
		self.cone_radius = 40    # cone diameter is 8 cm
		self.cone_radius_range = 0.40
		self.arena_padding = 80  # turning radius. keep sk8 in the arena.
		self.arena_margin = 40
		
		self.obj_settings = [ # class code      hue      sat      val     canny
		              ( self.clsCone,   0,  8,  42,100,  35,100,  82,127 ),
		              ( self.clsPadl,  52,106,  42,100,  41, 96,  82,127 ),
		              ( self.clsPadr, 258,335,  24, 76,  30, 85,  82,127 ),
		              ( self.clsSpot, 283,360,  46,100,  40,100,  82,127 )
		]
		self.magenta_settings = ( 10, 270,330,  50,100,  50,100,  82,127 ) # bright color swatch
		self.navy_settings    = ( 11, 181,352,   3, 58,   0, 33,  82,127 ) # tape, dark
		self.pumpkin_settings = ( 12,   3, 36,  80,100,  55, 86,  82,127 ) # tape, bright
		self.yellow_settings  = ( 13,  52, 76,  45, 93,  56, 82,  82,127 ) # tape, bright
		self.purple_settings  = ( 14, 244,360,  32, 52,  35, 82,  82,127 ) # tape, medium dark
		self.coral_settings   = ( 15, 321,360,  54,100,  48, 81,  82,127 ) # tape, bright but like cone
		self.ocean_settings   = ( 16, 184,260,  27, 69,  24, 50,  82,127 ) # tape, dark
		self.forest_settings  = ( 17,  60,181,  14,100,   2, 32,  82,127 ) # tape, dark
		self.barmax           = ( 18, 360,360, 100,100, 100,100, 255,255 )
		self.barnames = ( 'cls',  'hue_min', 'hue_max', 'sat_min', 'sat_max', 'val_min', 'val_max', 'canny_lo', 'canny_hi')
		self.clsname = [ 'cone','padl','padr','spot' ]

		# variables
		self.framenum = 0        # tello    nexus     pixel->prepd
		self.frameMap = False
		self.baseMap = False
		self.ovec = False  # orienting vector
		self.imgPrep = False
		self.posts = {}
		self.debugImages = []
		self.timesave = time.time()
	
		# aircraft altitude is measured in multiple ways
		#    agl - above ground level
		#    msl - mean sea level, based on 19-year averages
		#    barometric pressure, varies depending on the weather

		# baro reported by the tello is assumed to be MSL in meters to two decimal places
		#    a typical value before flying is 322.32
		#    the elevation of Chiang Mai is 310 meters

		# before takeoff, the camera is 20mm above the pad

		# all of our internal calculations are in mm

		self.pxlpermm = 0 # computed by the size of the pad, in pixels vs mm
		# the pxlpermm value implies an agl

	def reopenUI(self, cls):
		# read values from trackbars and print to log
		#settings = self.readSettings()
		#print(settings)

		# close the debug dialog window
		self.closeDebugDialog()

		# set new debugging class code
		self.clsdebug = cls

		# open a new debug dialog window
		self.openSettings()

	def isDebugging(self):
		return self.clsdebug > self.clsNone

	def openUI(self):
		if self.ui and self.isDebugging():
			self.openSettings()

	def closeDebugDialog(self):
		if self.ui and self.isDebugging():
			name = self.clsname[self.clsdebug]
			cv.destroyWindow(name)
	
	def closeUI(self):
		cv.destroyAllWindows()

	def post(self,key,value):
		self.posts[key] = value
		s = f'{key}={value}'
		logging.debug(s)
	
	def drawPosts(self,imgPost):
		linenum = 1
		ssave = ''
		for k in self.posts.keys():
			v = self.posts[k]
			s = f'{k}={v}'
			pt = (self.datalinemargin, self.datalineheight * linenum)
			cv.putText(imgPost, s, pt, cv.FONT_HERSHEY_SIMPLEX,.7,(0,0,0), 1)
			linenum += 1
			ssave += s + ';'
		if uni.soTrue(self.framenum, self.post_nth):
			logging.debug(ssave)
	
	def openSettings(self):
		# callback on track movement
		def on_trackbar(val):
			#jsettings = self.readSettings()
			#self.obj_settings[self.clsdebug] = settings
			return

		# open the dialog
		if self.ui and self.isDebugging():
			name = self.clsname[self.clsdebug]
			cv.namedWindow(name) # default WINDOW_AUTOSIZE, manual resizeable
			cv.resizeWindow( name,self.dialog_width, self.dialog_height)   # ignored with WINDOW_AUTOSIZE

			# create the trackbars
			settings = self.obj_settings[self.clsdebug]
			#for setting in settings:
			#	if setting != 'cls':
			#		cv.createTrackbar(setting, name, settings[setting], self.barmax[setting], on_trackbar)
			for n in range(1,9):
				barname = self.barnames[n]
				value = settings[n]
				maxvalue = self.barmax[n]
				cv.createTrackbar(barname, name, value, maxvalue, on_trackbar)
	
	def readSettings(self):
		# read the settings from the trackbars
		settings = self.obj_settings[self.clsdebug]
		windowname = self.clsname[self.clsdebug]
		#for setting in settings:
		#	if setting != 'cls':
		#		settings[setting] = cv.getTrackbarPos(setting, name)
		newset = [settings[0]]
		for n in range(1,9):
			barname = self.barnames[n]
			value = cv.getTrackbarPos(barname, windowname)
			newset.append(value)
		settings = tuple(newset)

		# create the color image for visualizing threshhold hsv values
		imgColor = self.createColorImage(settings)

		# show the color image within the dialog window
		cv.imshow(windowname, imgColor)
		self.obj_settings[self.clsdebug] = settings
		return settings

	def createColorImage(self, settings):
		# hsv, see https://alloyui.com/examples/color-picker/hsv.html

		# h = 6 primary colors, each with a 60 degree range, 6*60=360
		#     primary     red  yellow  green  cyan  blue  magenta  red
		#     hue degrees   0      60    120   180   240      300  359  360
		#     hue inRange   0      30     60    90   120      150  179  180
		# s = saturation as pct,        0=white, 100=pure color, at zero => gray scale
		# v = value "intensity" as pct, 0=black, 100=pure color, takes precedence over sat

		# trackbar settings are 360,100,100; convert to 0 to 1
		a = np.array(settings) / np.array(self.barmax)
		cls,hl,hu,sl,su,vl,vu,_,_ = a

		# colorsys values are all 0.0 to 1.0
		rl,gl,bl = colorsys.hsv_to_rgb(hl,sl,vl)
		ru,gu,bu = colorsys.hsv_to_rgb(hu,su,vu)

		# RBG and BGR valus are 0 to 255; convert from 0 to 1
		rl,ru,gl,gu,bl,bu = np.array([rl,ru,gl,gu,bl,bu]) * 255
		colormin = bl,gl,rl
		colormax = bu,gu,ru

		# again for hue only
		hrl,hgl,hbl = colorsys.hsv_to_rgb(hl,1.0,1.0)
		hru,hgu,hbu = colorsys.hsv_to_rgb(hu,1.0,1.0)
		hrl,hru,hgl,hgu,hbl,hbu = np.array([hrl,hru,hgl,hgu,hbl,hbu]) * 255
		huemin = hbl,hgl,hrl
		huemax = hbu,hgu,hru

		# an image is an array of numbers, depth 3, opencv uses BGR
		color_image_width = 200
		color_image_height = 100
		imgColor = np.zeros((color_image_height, color_image_width, 3), np.uint8) # blank image

		# divide images into four quadrants, top row is hue range, bottom row is hsv range
		for y in range(0, int(color_image_height/2)):
			for x in range(0, int(color_image_width/2)):
				imgColor[y,x] = huemin
			for x in range(int(color_image_width/2), color_image_width):
				imgColor[y,x] = huemax
		for y in range(int(color_image_height/2), color_image_height):
			for x in range(0, int(color_image_width/2)):
				imgColor[y,x] = colormin
			for x in range(int(color_image_width/2), color_image_width):
				imgColor[y,x] = colormax
		return imgColor
	
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
		pad = map.pad if map.pad else False
		spot = map.pad.spot if map.pad.spot else False
		cones = map.cones if map.cones else False
		arena = map.arena if map.arena else False

		# draw arena
		if arena:
			l = int(round(arena.bbox.l * self.pxlpermm))
			t = int(round(arena.bbox.t * self.pxlpermm))
			r = int(round(arena.bbox.r * self.pxlpermm))
			b = int(round(arena.bbox.b * self.pxlpermm))
			cv.rectangle(img, (l,t), (r,b), (127,0,0), 1)
	
		# draw cones
		if cones:
			r = int(round(self.cone_radius * self.pxlpermm))
			for cone in cones:
				#x = int(round(arena.bbox.center.x + (obj.bbox.center.x * self.frameWidth)))
				#y = int(round(arena.bbox.center.y + (obj.bbox.center.y * self.frameHeight)))
				x = int(round(cone.bbox.center.x * self.pxlpermm))
				y = int(round(cone.bbox.center.y * self.pxlpermm))
				cv.circle(img,(x,y),r,(0,0,255),1)
	
		# draw pad
		if pad:
			if pad.purpose == 'frame':
				if self.debugPad: # draw the halves
					if pad.padl:
						l = int(round(pad.padl.bbox.l * self.pxlpermm))
						t = int(round(pad.padl.bbox.t * self.pxlpermm))
						r = int(round(pad.padl.bbox.r * self.pxlpermm))
						b = int(round(pad.padl.bbox.b * self.pxlpermm))
						cv.rectangle(img, (l,t), (r,b), (0,255,255), 1) # BGR yellow, left

					if pad.padr:
						l = int(round(pad.padr.bbox.l * self.pxlpermm))
						t = int(round(pad.padr.bbox.t * self.pxlpermm))
						r = int(round(pad.padr.bbox.r * self.pxlpermm)) -1
						b = int(round(pad.padr.bbox.b * self.pxlpermm)) -1
						cv.rectangle(img, (l,t), (r,b), (255,0,255), 1) # BGR purple, right
				
					if pad.padl and pad.padr:
						drawPolygon(img, [pad.padl.bbox.center.tuple(), pad.padr.bbox.center.tuple(), pad.pt3.tuple()], self.pxlpermm)
				
				color = (0,0,0)
				#  outer perimeter
				r = round(self.pad_radius * self.pxlpermm)
				x = round(pad.center.x * self.pxlpermm)
				y = round(pad.center.y * self.pxlpermm)
				cv.circle(img,(x,y),r,color,1)

				# axis with arrow
				pt1, pt2 = calcLine((x,y), r, pad.angle)
				cv.line(img,pt1,pt2,color,1)  # center axis
				cv.circle(img,pt1,3,color,3)   # arrow pointing forward

			elif pad.purpose == 'home':
				# draw props
				r = round(self.pad_radius * self.pxlpermm)
				x = round(pad.center.x * self.pxlpermm)
				y = round(pad.center.y * self.pxlpermm)
				color = (255,128,128)
				radius_prop = .3 * r
				radius_xframe = .7 * r
				pta = []
				for a in [45,135,225,315]:
					ra = np.radians(a)
					xx = x + int(radius_xframe * np.cos(ra))
					xy = y + int(radius_xframe * np.sin(ra))
					pta.append((xx,xy))
					cv.circle(img,(xx,xy),int(radius_prop), color,2)

				# draw x-frame
				cv.line(img,pta[0],pta[2],color,4)  # center axis
				cv.line(img,pta[1],pta[3],color,4)  # center axis
				
				# draw drone body
				#cv.rectangle(img, (l,t), (r,b), (127,0,0), 1)

		if spot:
			color = (255,255,255)
			r = round(spot.bbox.radius * self.pxlpermm)
			x = round(spot.bbox.center.x * self.pxlpermm)
			y = round(spot.bbox.center.y * self.pxlpermm)
			cv.circle(img,(x,y),r,color,1)

	def drawUI(self):
		if not self.ui:
			return
		if not uni.soTrue(self.framenum, self.frame_nth):
			return

		img = self.imgPrep

		# create empty map
		imgMap = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
		imgMap.fill(255)  # made white
	
		# create final as copy of original
		imgFinal = img.copy()

		# draw maps
		if self.frameMap:
			self.drawMap(self.frameMap, imgMap)
			self.drawMap(self.frameMap, imgFinal)
		if self.baseMap:
			self.drawMap(self.baseMap, imgMap)
			self.drawMap(self.baseMap, imgFinal)

		# draw ovec
		if self.frameMap and self.baseMap:
			ptFrame = tuple(np.int0(np.array(self.frameMap.pad.center.tuple()) * self.pxlpermm))
			ptBase = tuple(np.int0(np.array(self.baseMap.pad.center.tuple()) * self.pxlpermm))
			color = (0,0,255)
			cv.line(imgMap,ptFrame,ptBase,color,3)  # ovec line between pads
			cv.line(imgFinal,ptFrame,ptBase,color,3)  # ovec line between pads

		# draw internal data calculations posted by programmer
		imgPost = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
		imgPost.fill(255)
		self.drawPosts(imgPost)
	
		# stack all images into one
		#imgTuple = ([imgMap,imgPost,imgFinal],)
		imgTuple = ([imgPost,imgFinal],)
		if self.isDebugging():
			imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = self.visualcortex.debugImages
			imgHsv= cv.cvtColor( imgHsv, cv.COLOR_HSV2BGR)
			imgTuple = ([imgPost,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgFinal])
			#imgTuple = ([imgPost,self.imgColor,imgMasked],[imgMap,imgFinal,imgCanny])
			#imgTuple = ([imgPost,imgMask,imgMasked],[imgMap,imgFinal,imgCanny])
		stack = self.stackImages(0.5,imgTuple)

		# show
		cv.imshow('Image Processing', stack)

#	#
#	# end UI section, begin image processing section
#	#
#
#	def detectObjectsNN(self,img):
#		pass
#
#	def detectObjectsCV(self,img):
#		objects = []
#		self.detectContours(img, self.obj_settings[self.clsCone], objects)
#		self.detectContours(img, self.obj_settings[self.clsPadl], objects)
#		self.detectContours(img, self.obj_settings[self.clsPadr], objects)
#		self.detectContours(img, self.obj_settings[self.clsSpot], objects)
#		return objects
#
#	def detectContours(self,img,settings,objects):
#		# draw a one-pixel black border around the whole image
#		#	when the drone is on the pad, 
#		#	each halfpad object extends past the image boundary on three sides, 
#		#	and findContours detects only the remaining edge as an object
#		cv.rectangle(img, (0,0), (self.frameWidth-1,self.frameHeight-1), (0,0,0), 1)
#
#		# mask based on hsv ranges
#		# settings are 0 to 360,100,100
#
#		# opencv values are 0 to 179,255,255
#		# trackbar settings are 360,100,100
#		#hl = settings['hue_min'] / 2  # 0 to 360 degrees
#		#hu = settings['hue_max'] / 2
#		#sl = int((settings['sat_min'] / self.barmax['sat_min']) * 255)  # 0 to 100 pct
#		#su = int((settings['sat_max'] / self.barmax['sat_max']) * 255)
#		#vl = int((settings['val_min'] / self.barmax['val_min']) * 255)  # 0 to 100 pct
#		#vu = int((settings['val_max'] / self.barmax['val_max']) * 255)
#
#		cls,hl,hu,sl,su,vl,vu,cl,cu = settings
#		hl = int(hl / 2)
#		hu = int(hu / 2)
#		sl = int((sl / self.barmax[3]) * 255)  # 0 to 100 pct
#		su = int((su / self.barmax[4]) * 255)
#		vl = int((vl / self.barmax[5]) * 255)  # 0 to 100 pct
#		vu = int((vu / self.barmax[6]) * 255)
#
#		#lower = np.array([(settings['hue_min']/2),settings['sat_min'],settings['val_min']])
#		#upper = np.array([(settings['hue_max']/2),settings['sat_max'],settings['val_max']])
#		lower = np.array([hl,sl,vl])
#		upper = np.array([hu,su,vu])
#		imgHsv = cv.cvtColor(img,cv.COLOR_BGR2HSV)
#		imgMask = cv.inRange(imgHsv,lower,upper) # choose pixels by hsv threshholds
#		imgMasked = cv.bitwise_and(img,img, mask=imgMask)
#	
#		imgBlur = cv.GaussianBlur(imgMasked, (17, 17), 1)  # started at (7,7);  the bigger kernel size pulls together the pieces of padr
#		imgGray = cv.cvtColor(imgBlur, cv.COLOR_BGR2GRAY)
#	
#		# canny: edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
#		imgCanny = cv.Canny(imgGray, cl, cu)
#	
#		# dilate: thicken the line
#		kernel = np.ones((5, 5))
#		imgDilate = cv.dilate(imgCanny, kernel, iterations=1)
#
#		# get a data array of polygons, one contour boundary for each object
#		contours, _ = cv.findContours(imgDilate, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
#		if self.clsdebug == cls:
#			self.debugImages = [imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate]
#
#		# get bounding box for each contour
#		for contour in contours:
#			area = cv.contourArea(contour)
#			perimeter = cv.arcLength(contour, True)
#			polygon = cv.approxPolyDP(contour, 0.02 * perimeter, True)
#			l,t,w,h = cv.boundingRect(polygon)
#
#			tl = round(l/self.frameWidth, 6)
#			tt = round(t/self.frameHeight, 6)
#			tw = round(w/self.frameWidth, 6)
#			th = round(h/self.frameHeight, 6)
#
#			bbox = Bbox(tl,tt,tw,th)
#			obj = DetectedObject(cls, bbox)
#			objects.append(obj)
#		return

	def findSpot(self, objects, pad):
		spota = []
		for obj in objects:
			if obj.cls == self.clsSpot:
				spota.append(obj)

		self.post('num spot', len(spota))
		if len(spota) <= 0:
			return False

		# if multiples, choose the one with the largest radius 
		objspot = spota[0]
		for obj in spota:
			#if pad and not pad.getBbox().intersects(obj.bbox):
			#	continue
			if obj.bbox.radius > objspot.bbox.radius:
				objspot = obj

		# go back and scrub objects list
		for obj in objects:
			if obj.cls == self.clsSpot and obj is not objspot:
				objects.remove(obj)

		# from pct to pxl
		bbox = copy.deepcopy(objspot.bbox)
		bbox.l *= self.frameWidth
		bbox.t *= self.frameHeight
		bbox.w *= self.frameWidth 
		bbox.h *= self.frameHeight 
		bbox.calc()  # calc center, radius

		# conversion factor pxl per mm
		pxlpermm = bbox.radius / self.spot_radius
		self.post('spot pxl diam', bbox.diameter)
		self.post('spot pxlpermm', pxlpermm)

		spot = Spot(bbox,pxlpermm) # units=pxl
		return spot

	def findHalf(self, objects, cls):
		clsname = 'left' if cls == self.clsPadl else 'right' # for posts

		a = []
		for obj in objects:
			if obj.cls == cls:
				a.append(obj)
		self.post(f'pad {clsname}', len(a))

		# ideally we have one and only one
		o = False
		halfmax = False
		if len(a) >= 1:
			o = a[0]
			halfmax = copy.deepcopy(a[0])
		else:
			logging.debug(f'missing half {clsname}')

		# if multiples, choose the one with the largest radius 
		# or combine them all into one big one
		if len(a) > 1:
			for obj in a:
				if obj.bbox.radius > o.bbox.radius:
					o = obj
				halfmax.bbox.enlarge(obj.bbox)

			# go back and scrub objects list
			for obj in objects:
				if obj.cls == cls and obj is not o:
					objects.remove(obj)

		# from pct to pxl
		half = copy.deepcopy(o)
		if half:
			half.bbox.l *= self.frameWidth
			half.bbox.t *= self.frameHeight
			half.bbox.w *= self.frameWidth 
			half.bbox.h *= self.frameHeight 
			half.bbox.calc()

		# i have not tested halfmax
		# instead I increased the kernel size of the Gaussian Blur
		if halfmax:
			halfmax.bbox.l *= self.frameWidth
			halfmax.bbox.t *= self.frameHeight
			halfmax.bbox.w *= self.frameWidth 
			halfmax.bbox.h *= self.frameHeight 
			halfmax.bbox.calc()
		return half, halfmax

	def findPad(self, objects):
		padl, padlmax = self.findHalf(objects, self.clsPadl)
		padr, padrmax = self.findHalf(objects, self.clsPadr)

		#padr = padrmax

		# padr and padl are expected to intersect (unless perfectly straight up)
		if padl and padr and not padl.bbox.intersects( padr.bbox):
			logging.debug('pad halves do not intersect')

		if padl and not padr:
			padr = copy.deepcopy(padl)
			padr.bbox.l += (padr.bbox.w)
			padr.bbox.calc()
		if padr and not padl:
			padl = copy.deepcopy(padr)
			padl.bbox.l -= (padl.bbox.w)
			padl.bbox.calc()

		pad = Pad(padl, padr)

		# is pad complete?
		if padl and padr:
			if padl.bbox.touchesEdge(self.frameWidth,self.frameHeight) \
			or padr.bbox.touchesEdge(self.frameWidth,self.frameHeight):
				pad.half_state = 'partial'
			else:
				pad.half_state = 'complete'
		else:
			pad.half_state = 'missing'
		self.post('pad half state', pad.half_state)

		spot = self.findSpot(objects, pad)
		pad.spot = spot

		# calc conversion factor
		pad.calc()
		pad.pxlpermm = pad.radius / self.pad_radius
		self.post('pad pxl diam', pad.diameter)
		self.post('pad pxlpermm', pad.pxlpermm)

		# using pad or spot
		if pad.half_state == 'complete':
			pad.state = 'pad'
		elif spot:
			pad.state = 'spot'
		#elif pad.half_state == 'partial':
		#	pad.state = 'pad'
		else:
			pad.state = 'missing' # no pad, no spot

		# choose pad or spot
		if pad.state == 'pad':
			self.pxlpermm = pad.pxlpermm
		elif pad.state == 'spot':
			self.pxlpermm = spot.pxlpermm
		if self.pxlpermm == 0.0:		
			pad.state = 'missing'
		self.post('pad state', pad.state)
		self.post('final pxlpermm', self.pxlpermm)

		# convert to mm, calc radius
		if pad.state != 'missing':
			if pad.padl:
				pad.padl.bbox.l /= self.pxlpermm
				pad.padl.bbox.t /= self.pxlpermm
				pad.padl.bbox.w /= self.pxlpermm
				pad.padl.bbox.h /= self.pxlpermm
				pad.padl.bbox.calc()
			if pad.padr:
				pad.padr.bbox.l /= self.pxlpermm
				pad.padr.bbox.t /= self.pxlpermm
				pad.padr.bbox.w /= self.pxlpermm
				pad.padr.bbox.h /= self.pxlpermm
				pad.padr.bbox.calc()
			if spot:
				spot.bbox.l /= self.pxlpermm
				spot.bbox.t /= self.pxlpermm
				spot.bbox.w /= self.pxlpermm
				spot.bbox.h /= self.pxlpermm
				spot.bbox.calc()

			pad.calc()

			if pad.state == 'spot':
				pad.center.x = spot.bbox.center.x
				pad.center.y = spot.bbox.center.y # + self.spot_offset
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
		if len(cones) <= 0:
			cones = False
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
		if not cones:
			return False

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

	def saveTrain(self,img,objects):
		ht = 0
		fname = f'{self.dirtrain}/{self.framenum}.txt'
		f = open(fname, 'a')

		for obj in objects:
			f.write(f"{obj.cls} {obj.bbox.t} {obj.bbox.l} {obj.bbox.w} {obj.bbox.h}\n")
		f.close()

	def start(self):
		logging.info('hippocampus starting')
		if self.ui:
			self.openUI()
			logging.info('UI opened')
		if self.save_mission:
			self.dirframe = uni.makedir('frame')
			self.dirtrain = uni.makedir('train')

		self.visualcortex = visualcortex.VisualCortex()
 
	def stop(self):
		logging.info('hippocampus stopping')
		self.closeUI()

	def buildMap(self,objects):
		pad = self.findPad(objects)
		cones = False
		arena = False
		if pad.state != 'missing':
			cones = self.findCones(objects)
			arena = self.findArena(cones)
		map = Map(pad, cones, arena)
		return map
	
	def processFrame(self,img, framenum, teldata):
		self.framenum += 1
		ovec = False
		rccmd = 'rc 0 0 0 0'

		if not uni.soTrue(self.framenum, self.frame_nth):
			return ovec,rccmd

		self.post('input frame num', framenum)
		self.post('frame num', self.framenum)

		self.imgPrep = img # save for use by drawUI

		# get settings from trackbars
		if self.ui:
			self.readSettings()

		# detect objects - unit: percent of frame
		#self.objects = self.detectObjects(img)
		self.objects = self.visualcortex.detectObjects(img)
		self.post('objects found',len(self.objects))

		# build map
		self.frameMap = self.buildMap(self.objects)
		if not self.frameMap:
			return ovec,rccmd

		self.post('pxlpermm',self.pxlpermm)
		if teldata:
			aglin = teldata['agl']
			self.post('agl input', aglin)

		# calc agl
		self.agl = aglFromPxpmm(self.pxlpermm)
		self.post('agl', self.agl)

		# first time, save base  ??? periodically make new base
		#if True: #not self.baseMap:
		if self.pxlpermm > 0.0:
				
			# why is pad center below and to the right of the two halves
			#      only when there is no spot?
			
			# if padr is fragmented in the shadow of padl, try combining all instead of taking the biggest
			#     goal is same area between padr and padl
			#     padl and padr should be adjacent, overlapping, and have the same area

			# create function for pxlpermm to agl
			#     be cautious of the 640px across, because of the angle of the lens
			# Take triangulation into account when trying to size objects on the ground
			#     Note the difference between objects directly under the aircraft,
			#     and objects out on the perimeter.
			pxlpermm_at_20_mm    = 24.61  # shows 26mm across, 640/26, parked
			pxlpermm_at_20_mm2   =  4.60  # currently calculated
			pxlpermm_pad_visible =  2.19  # agl ?
			pxlpermm_at_1_meter  =  0.70  # mm across?
			pxlpermm_at_2_meter  =  0.30  # mm across?

			self.baseMap = copy.deepcopy(self.frameMap)
			self.baseMap.pad.purpose = 'home'
			
			# for hover on pad
			# here, baseMap means desired position: dead center, straight up, 1 meter agl
			x = (self.frameWidth/2) / self.pxlpermm
			y = (self.frameHeight/2) / self.pxlpermm
			self.baseMap.pad.center = Pt(x,y)
			self.baseMap.pad.angle = 0 
			self.baseMap.pad.radius = (self.frameHeight/2) / pxlpermm_at_1_meter

			# orient frame to map
			angle,radius,_ = triangulateTwoPoints( self.baseMap.pad.center, self.frameMap.pad.center)
			# use this to navigate angle and radius, to counteract drift
			# assume stable agl and no yaw, so angle and radius refers to drift
			# in this case, drawing basemap over framemap results only in offset, not rotation or scale
			
			# compare frameMap to baseMap, current position to desired position
			diffx,diffy = np.array(self.frameMap.pad.center.tuple()) - np.array(self.baseMap.pad.center.tuple())

			#diffagl agl in mm, calculated as function of pxlpermm, also proportional to home radius

			#diffangle, angle, comparison of base to home

			ovec = (diffx, diffy, 0, 0)

		# compare pad angle and radius between basemap and framemap
		# use this to reorient frame to map
		# rotate basemap and draw on top of frame image
		# rotate framemap and frameimg and draw underneath basemap

		if ovec:
			rccmd = uni.composeRcCommand(ovec)
			self.post('nav cmd', rccmd)

		# save mission parameters - frame, train, mission - done in mode fly, not sim
		if self.save_mission:
			fname = f"{uni.makedir('frame')}/{framenum}.jpg"
			cv.imwrite(fname,self.imgPrep)
			self.saveTrain(img, self.objects)
			self.logMission('sdata', rccmd)

		# display through portal to human observer
		self.drawUI()

		return ovec,rccmd

	# the hippocampus does all the memory, the drone has no memory
	def logMission(self, sdata, rccmd):
		# missing sdata, rccmd, agl, ddata['agl'] ; diff between framenum and self.framenum
		ts = time.time()
		tsd = ts - self.timesave
		src = rccmd.replace(' ','.')
		prefix = f"rc:{src};ts:{ts};tsd:{tsd};fn:{self.framenum};agl:{self.agl};"
		self.timesave = ts
		logging.log(logging.MISSION, prefix + sdata)

if __name__ == '__main__':
	# run a drone simulator
	uni.configureLogging('sim')
	logging.debug('')
	logging.debug('')

	# sim with frames only
	dir = '/home/john/sk8/bench/testcase'        # 1-5
	dir = '/home/john/sk8/bench/20210511-113944' # start at 201
	dir = '/home/john/sk8/bench/20210511-115238' # start at 206
	dir = '/home/john/sk8/bench/aglcalc'         # 15 frames by agl in mm

	# sim with mission log
	dir = '/home/john/sk8/fly/20210512/095147'  # manual stand to two meters
	dir = '/home/john/sk8/fly/20210512/143128' # on the ground with tape measure
	dir = '/home/john/sk8/fly/20210512/161543'  # 5 steps of 200 mm each
	dir = '/home/john/sk8/fly/20210512/212141'  # 30,50,100,120,140,160,180,200 mm
	dir = '/home/john/sk8/fly/20210512/224139'  # 150, 200 mm agl
	
	dir = '/home/john/sk8/fly/20210514/172116'  # agl calc

	# input simulator data
	dirframe = f'{dir}/frame'
	missiondatainput  = f'{dir}/mission.log'
	missiondata = None
	try:	
		fh = open(missiondatainput)
		missiondata = fh.readlines()
		lastline = len(missiondata)
		logging.info('mission log found')
	except:
		logging.info('mission log not found')

	# start as simulator
	hippocampus = Hippocampus(ui=True, save_mission=False)
	hippocampus.start()
	framenum = 1
	dline = None
	while True:
		# read one line from the mission log, optional
		#if fh:
		#	line = fh.readline()
		#	m = re.search( r';fn:(.*?);', line)
		#	framenum = m.group(1)
		if missiondata:
			sline = missiondata[framenum-1]	
			dline = uni.unpack(sline)

		# read the frame
		fname = f'{dirframe}/{framenum}.jpg'
		frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
		if frame is None:
			logging.error(f'file not found: {fname}')
			break;

		# process the frame
		ovec = hippocampus.processFrame(frame, framenum, dline)

		# kill switch
		k = cv.waitKey(1)  # in milliseconds, must be integer
		if k & 0xFF == ord('n'):
			if framenum < lastline:
				framenum += 1
			continue
		elif k & 0xFF == ord('p'):
			if framenum > 1:
				framenum -= 1
			continue
		elif k & 0xFF == ord('r'):
			continue
		elif k & 0xFF == ord('s'):
			self.saveTrain()
			continue
		elif k & 0xFF == ord('0'):
			hippocampus.reopenUI(0)
			continue
		elif k & 0xFF == ord('1'):
			hippocampus.reopenUI(1)
			continue
		elif k & 0xFF == ord('2'):
			hippocampus.reopenUI(2)
			continue
		elif k & 0xFF == ord('3'):
			hippocampus.reopenUI(3)
			continue
		elif k & 0xFF == ord('q'):
			break;

	hippocampus.stop()

'''
class Hippocampus
	Public methods:
		start()
		processFrame(img,framenum,telemetry)
			detectObjects - visual cortex, pareital lobe, occipital lobe, Brodmann area
			buildMap - hippocampus, retrosplenial cortex
		drawUI()
		stop()

	four items are saved to disk
		1. frames, already flipped for mirror, no resize
		2. training file, detected objects, must match frame
		3. mission log, logging level 17 only
		4. debug log, logging all levels

		Notes on data saving: 
			the Hippocampus is the only object to access the disk (except for debug log)
			see universal.py for folder and filename settings
			console log does NOT display levels debug and mission.
			frames and mission log can be used to rerun a mission in the simulator.
			when flying the drone, we save frames and mission log
				when flying the simulator, we do not
			training files:
				saved automaically during flight
				can optionally be rewritten during sim
				can be rewritten one frame at a time on-demand during sim

todo

1. benchmark flight(s), manual
	a. ground to 2 meters
	b. drift to all four quadrants
	c. rotation to four quadrants
	d. test cases
		angle of pad, 4 quadrants
		on the ground
		missing left
		missing right
		missing cones
		missing left, right, cones

2. execute rc command, to hover over pad

3. mirror calibration

4. write liftoff and land maneuvers

5. calculate and execute a course, after mastering hover

6. remove pad and use basemap with cones alone
	- rotate basemap for best shape arena
	- orient each frame to the basemap
	- orient each frame to the basemap, even when the frame shows only a portion of the basemap

7. orientation
	three overlays: map, frame, sk8
		1. map - "basemap" centered and angled on arena, plus home
		2. frame - momentary position of tello, "base" has radius of tello as virtual pad
		3. pad - momentary position of sk8, often obscurred, temporarily fixed
	todo:	
		- rotate arena and enlarge to base map
		- add home to base map
		- superimpose map onto frame, frameMap matches frame by definition
		- underimpose frame under basemap
			- match frame to portion of map
	dead reckoning
		when pad and arena is lost
		go with previous calculations

8. matrix math
	use tuple for point and list for vector
	use np.array() for matrix math among points and vectors
	all points and vectors are 4D, ? the only point in the air is the tello
	a point on the ground can have a yaw angle, z is always 0

9. save video
	x all memory saving in Hippocampus, none in Drone
	saveTrain on-demand, in Sim
	snap Frame to bench on-demand, in Sim
	x keep nth option, superior to true/false
	x filename: folder by day, folder by mission, frame number, jpgs only
	mission clock, elapsed time between frames
	file-modified timestamp, does it match mission clock?
	x save flipped image, no resizing
	when resizing is stopped, recalc agl factor, change hyperbola k
	x change all saved frames
	rerun sim all test cases, rewrite training and mission logs
	

10. fix rc compose to use body coordinates instead of ground coordinates

11. photo angle correction

12. write Prefrontal

class Prefrontal:
	def getCourseVector()
	two instances, one for drone, one for skate	
	queue of maneuvers
	default hover method between requests
	maneuvers:
		hover
		perimeter
		calibrate
		home, proceed to
		pad, proceed to
		lower until pad no longer visible
		land
	if flight-time exceeded
		which brain part does this?
		same as battery check
		maybe build the main loop into a method somewhere

Brain parts
	Hippocampus
		spatial orientation and cartography
		enabled by memory: remembers where you have been by building a map
	Prefrontal
		navigation
		plans a route forward
		based on the map provided by the Hippocampus

The final vector passed to RC, is composed of two vectors:
	hippocampus: drift correction
	prefrontal: course correction	

This article compares Hippocampus and Frontal Cortex.
https://www.sciencenewsforstudents.org/article/two-brain-areas-team-make-mental-maps 

'''
