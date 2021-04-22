'''
hippocamapus.py - object detection by color

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

class Pt:
	def __init__(self, x, y):
		self.x = x
		self.y = y
	
	def averageTwoPoints(self, pt2):
		x2= pt2.x
		y2= pt2.y
		xc = self.x + ((x2 - self.x) / 2)
		yc = self.y + ((y2 - self.y) / 2)
		return Pt(xc,yc)
	
	def triangulateTwoPoints(self, pt2):
		# length of hypotenuse
		lenx = abs(self.x - pt2.x)
		leny = abs(self.y - pt2.y)
		hypotenuse = np.sqrt(lenx**2 + leny**2)

		# point r, the right angle
		ptr = Pt(self.x+lenx, self.y+leny)

		# angle of the hypotenuse to the vertical axis
		# see https://www.geogebra.org/classic/h6pgbftp
		oa = lenx/leny if (leny != 0) else 0 # tangent of angle = opposite over adjacent 
		radians = np.arctan(oa)
		degrs = np.degrees(radians)
		return degrs, hypotenuse, ptr
		
	def __str__(self):
		return f'({self.x},{self.y})'

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
		self.center = self.padl.bbox.center.averageTwoPoints(self.padr.bbox.center)
		self.angle,self.radius,_ = self.padl.bbox.center.triangulateTwoPoints(self.padr.bbox.center)

class Arena:
	def __init__(self,bbox):
		self.bbox = bbox

class Map:
	def __init__(self):
		self.cones = False
		self.pad = False
		self.arena = False

class Hippocampus:
	def __init__(self, ui=True, saveTrain=True):
		self.ui = ui
		self.saveTrain = saveTrain

		# settings
		self.debugCones = False 
		self.debugLzr = False
		self.debugLzl =  False
		self.datalineheight = 22
		self.datalinemargin = 5

		self.useNeuralNet = False

		self.save_train_nth = 10
		self.save_post_nth = 60

		self.outfolderbase = '/home/john/sk8/images/'

		self.pad_radius = 70     # pad is 14 cm square
		self.cone_radius = 40    # cone diameter is 8 cm
		self.cone_radius_range = 0.20
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

		self.clsCone = 0 # object classification codes
		self.clsPadl = 1
		self.clsPadr = 2

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
		self.imgInt = False
		self.internals = {}
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
			if self.debugCones:
				self.openSettings(self.cone_settings, 'Cone')
			elif self.debugLzr:
				self.openSettings(self.padr_settings, 'LZR')
			elif self.debugLzl:
				self.openSettings(self.padl_settings, 'LZL')

	def closeUI(self):
		if self.ui:
			cv.destroyAllWindows()

	def post(self,key,value):
		self.internals[key] = value
	
	def drawInternals(self):
		linenum = 1
		ssave = ''
		for k in self.internals.keys():
			v = self.internals[k]
			s = f'{k}={v}'
			pt = (self.datalinemargin, self.datalineheight * linenum)
			cv.putText(self.imgInt, s, pt, cv.FONT_HERSHEY_SIMPLEX,.7,(0,0,0), 1)
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
			cv.createTrackbar(setting, window_name, settings[setting], self.barmax[setting],empty)
	
	def readSettings(self, settings, name):
		window_name = f'{name} Settings'
		for setting in settings:
			settings[setting] = cv.getTrackbarPos(setting, window_name)
	
	def stackImages(self,scale,imgArray):
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
	
	def drawMap(self, arena, cones, pad, img):
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
			r = round(self.pad_radius * self.pxlpermm)
			#x = round((arena.bbox.l + pad.center.x) * self.pxlpermm)
			#y = round((arena.bbox.t + pad.center.y) * self.pxlpermm)
			x = round(pad.center.x * self.pxlpermm)
			y = round(pad.center.y * self.pxlpermm)
			cv.circle(img,(x,y),r,(255,0,255),1)  # outer perimeter

			pt1, pt2 = self.calcLine((x,y), r, pad.angle)
			cv.line(img,pt1,pt2,(255,0,255),1)  # center axis

			pt = pt1 if pt1[0] < pt2[0] else pt2 # which end is up?
			cv.circle(img,pt,3,(255,0,255),1)   # arrow pointing forward
	
	def calcLine(self,c,r,a):
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
		return (x1,y1), (x2,y2) 
	
	def drawUI(self, img):
		if self.ui:
			# map
			imgMap = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
			imgMap.fill(255)
			self.drawMap(self.arena, self.cones, self.pad, imgMap)
		
			# frame overlaid with oriented map
			imgFinal = img.copy()
			self.drawMap(self.arena, self.cones, self.pad, imgFinal)

			# internals, values, coefficients, scalars, multipliers, calculations, factors
			# hippocampus internal data calculations
			self.imgInt = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
			self.imgInt.fill(255)
			self.drawInternals()
	
			stack = self.stackImages(0.7,([imgMap,self.imgInt,imgFinal]))
			if self.debugCones or self.debugLzr or self.debugLzl:
				imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = self.debugImages
				stack = self.stackImages(0.7,([self.imgInt,imgHsv,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal]))
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

		# if multiples, choose the one with the largest radius 
		objpadl = False
		radius = 0
		for obj in padla:
			if obj.bbox.radius > radius:
				objpadl = obj
		objpadr = False
		radius = 0
		for obj in padra:
			if obj.bbox.radius > radius:
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
			logging.warning('pad halves do not intersect')

		# from pct to pxl
		padr = copy.deepcopy(objpadr)
		padr.bbox.l *= self.frameWidth
		padr.bbox.t *= self.frameHeight
		padr.bbox.w *= self.frameWidth 
		padr.bbox.h *= self.frameHeight 
		padr.bbox.calc()

		padl = copy.deepcopy(objpadl)
		padl.bbox.l *= self.frameWidth
		padl.bbox.t *= self.frameHeight
		padl.bbox.w *= self.frameWidth 
		padl.bbox.h *= self.frameHeight 
		padl.bbox.calc()

		# calc pad radius in pixels
		#_,pxlPadRadius,_ = padl.bbox.center.triangulateTwoPoints(padr.bbox.center)
		pxlpadcenter = padl.bbox.center.averageTwoPoints(padr.bbox.center)
		pxlpt2 = Pt(padr.bbox.l, padl.bbox.t)
		_,pxlPadRadius,_ = pxlpadcenter.triangulateTwoPoints(pxlpt2)

		# conversion factor pxl per mm
		# nb: conversion factor implies an agl
		self.pxlpermm = pxlPadRadius / self.pad_radius

		# from pxl to mm
		padr.bbox.l /= self.pxlpermm
		padr.bbox.t /= self.pxlpermm
		padr.bbox.w /= self.pxlpermm
		padr.bbox.h /= self.pxlpermm
		padr.bbox.calc()

		padl.bbox.l /= self.pxlpermm
		padl.bbox.t /= self.pxlpermm
		padl.bbox.w /= self.pxlpermm
		padl.bbox.h /= self.pxlpermm
		padl.bbox.calc()

		# create pad object in mm
		pad = Pad(padl,padr)
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
				else:
					objects.remove(obj)

		self.post('cones found', numconeobjs)
		self.post('cones accepted', len(cones))
		return cones
		
	def findArena(self, cones):
		# make an array of points and pass it to cv.RotatedRect()
		#pta = np.empty((0,0))
		#for cone in cones:	
		#	pt = cv.Point2f(cone.center.x,cone.center.y)
		#	pta.append(pt)
		#rect = cv.minAreaRect(pta)

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

	def processFrame(self,img,baro_agl):
		self.baro_agl = baro_agl
		self.framenum += 1
		self.frameHeight,self.frameWidth,self.frameDepth = img.shape

		self.post('image_dim', f'h:{self.frameHeight},w:{self.frameWidth},d:{self.frameDepth}')

		# get settings from trackbars
		if self.ui:
			if self.debugCones:
				self.readSettings( self.cone_settings, 'Cone')
			elif self.debugLzr:
				self.readSettings( self.padr_settings, 'LZR')
			elif self.debugLzl:
				self.readSettings( self.padl_settings, 'LZL')

		# detect objects - unit: percent of frame
		self.objects = self.detectObjects(img)
		self.post('objects found',len(self.objects))

		# build map
		self.pad = self.findPad(self.objects)
		self.post('pad center', self.pad.center)
		self.post('pad angle' , self.pad.angle)
		self.post('pad radius', self.pad.radius)

		self.cones = self.findCones(self.objects)
		self.arena = self.findArena(self.cones)

		# orient frame to map

		# save image and objects for mission debriefing and neural net training
		self.saveTrainingData(img, self.objects)

	def parseFilenameForHeight(self, fname):
		height = int(fname.split('_ht_')[1].split('.')[0])
		return height

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
	imgfile = 'sk8_2_meter_ht_2000.jpg'
	imgfile = 'sk8_1_meter_ht_1000.jpg'

	hippocampus = Hippocampus(True, True)
	hippocampus.start()

	while True:
		ht = hippocampus.parseFilenameForHeight(imgfile)
		img = cv.imread(imgfolder+imgfile, cv.IMREAD_UNCHANGED)
		hippocampus.processFrame(img, ht)
		hippocampus.drawUI(img)
		if cv.waitKey(1) & 0xFF == ord('q'):
			break

	hippocampus.stop()

