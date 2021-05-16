'''
visualcortex.py - class VisualCortex, edge detection
'''
import cv2 as cv
import numpy as np
#from datetime import datetime
#import time
#import logging
#import os
#import copy
#import colorsys
#import re
#import universal
import sk8math

# rename to Edge?
class DetectedObject:
	def __init__(self, cls, bbox, inputunits=False):
		self.cls = cls
		self.bbox = bbox

	def __str__(self):
		return f'{self.cls}: {self.bbox}'

class VisualCortex:
	def __init__(self):
		self.use_neural_net = False

		# object classification codes
		self.clsNone = -1
		self.clsCone = 0
		self.clsPadl = 1
		self.clsPadr = 2
		self.clsSpot = 3

		# change name to edge_threshholds
		self.obj_settings = [ 
			# class code      hue      sat      val     canny
			( self.clsCone,   0,  8,  42,100,  35,100,  82,127 ),
			( self.clsPadl,  52,106,  42,100,  41, 96,  82,127 ),
			( self.clsPadr, 258,335,  24, 76,  30, 85,  82,127 ),
			( self.clsSpot, 283,360,  46,100,  40,100,  82,127 )
		]

		self.imgWid = 0
		self.imgHt = 0
		self.debugImages = []

		#self.magenta_settings = ( 10, 270,330,  50,100,  50,100,  82,127 ) # bright color swatch
		#self.navy_settings    = ( 11, 181,352,   3, 58,   0, 33,  82,127 ) # tape, dark
		#self.pumpkin_settings = ( 12,   3, 36,  80,100,  55, 86,  82,127 ) # tape, bright
		#self.yellow_settings  = ( 13,  52, 76,  45, 93,  56, 82,  82,127 ) # tape, bright
		#self.purple_settings  = ( 14, 244,360,  32, 52,  35, 82,  82,127 ) # tape, medium dark
		#self.coral_settings   = ( 15, 321,360,  54,100,  48, 81,  82,127 ) # tape, bright but like cone
		#self.ocean_settings   = ( 16, 184,260,  27, 69,  24, 50,  82,127 ) # tape, dark
		#self.forest_settings  = ( 17,  60,181,  14,100,   2, 32,  82,127 ) # tape, dark
		#self.barmax           = ( 18, 360,360, 100,100, 100,100, 255,255 )
		#self.barnames = ( 'cls',  'hue_min', 'hue_max', 'sat_min', 'sat_max', 'val_min', 'val_max', 'canny_lo', 'canny_hi')
		#self.clsname = [ 'cone','padl','padr','spot' ]

#
#		# object classification codes
#		self.clsNone = -1
#		self.clsCone = 0
#		self.clsPadl = 1
#		self.clsPadr = 2
#		self.clsSpot = 3
#
#		# settings
#		self.clsdebug = self.clsCone
#		self.debugPad = True 
#
#		self.dialog_width = 480
#		self.dialog_height = 480
#
#		self.frameWidth  = 960
#		self.frameHeight = 720
#		self.frameDepth  = 3
#
#		self.datalineheight = 22
#		self.datalinemargin = 5
#
#
#		self.frame_nth = 1
#		self.post_nth = 0
#
#		self.spot_radius = 8     # spot is 16 mm diameter
#		self.spot_offset = 46    # spot center is 46 mm forward of pad center
#		self.pad_radius = 70     # pad is 14 cm square
#		self.cone_radius = 40    # cone diameter is 8 cm
#		self.cone_radius_range = 0.40
#		self.arena_padding = 80  # turning radius. keep sk8 in the arena.
#		self.arena_margin = 40
#		
#		# variables
#		self.framenum = 0        # tello    nexus     pixel->prepd
#		self.frameMap = False
#		self.baseMap = False
#		self.ovec = False  # orienting vector
#		self.imgPrep = False
#		self.posts = {}
#		self.timesave = time.time()
#	
#		# aircraft altitude is measured in multiple ways
#		#    agl - above ground level
#		#    msl - mean sea level, based on 19-year averages
#		#    barometric pressure, varies depending on the weather
#
#		# baro reported by the tello is assumed to be MSL in meters to two decimal places
#		#    a typical value before flying is 322.32
#		#    the elevation of Chiang Mai is 310 meters
#
#		# before takeoff, the camera is 20mm above the pad
#
#		# all of our internal calculations are in mm
#
#		self.pxlpermm = 0 # computed by the size of the pad, in pixels vs mm
#		# the pxlpermm value implies an agl

	def detectObjects(self,img):
		self.img = img
		if self.use_neural_net:
			pass
		else:
			self.imgHt,self.imgWid,_ = img.shape
			objects = []
			settings = self.obj_settings
			for cls in range(len(settings)): 
				self.detectContours(img,settings[cls],objects,3)

		#self.detectContours(img, self.obj_settings[self.clsCone], objects)
		#self.detectContours(img, self.obj_settings[self.clsPadl], objects)
		#self.detectContours(img, self.obj_settings[self.clsPadr], objects)
		#self.detectContours(img, self.obj_settings[self.clsSpot], objects)
		return objects

	def detectContours(self,img,settings,objects,clsdebug):
		# draw a one-pixel black border around the whole image
		#	When the drone is on the pad, 
		#	each halfpad object extends past the image boundary on three sides, 
		#	and cv.findContours() detects only the remaining edge as an object.
		cv.rectangle(img, (0,0), (self.imgWid-1,self.imgHt-1), (0,0,0), 1)

		# mask based on hsv ranges
		# settings are 0 to 360,100,100

		# opencv values are 0 to 179,255,255
		# trackbar settings are 360,100,100
		#hl = settings['hue_min'] / 2  # 0 to 360 degrees
		#hu = settings['hue_max'] / 2
		#sl = int((settings['sat_min'] / self.barmax['sat_min']) * 255)  # 0 to 100 pct
		#su = int((settings['sat_max'] / self.barmax['sat_max']) * 255)
		#vl = int((settings['val_min'] / self.barmax['val_min']) * 255)  # 0 to 100 pct
		#vu = int((settings['val_max'] / self.barmax['val_max']) * 255)

		# unpack threshholds
		#cls,hl,hu,sl,su,vl,vu,cl,cu = settings

		# color coordinate systems
		# most systems use RGB: 255,255,255
		# openCV by default uses BGR: 255,255,255

		# sk8 HSV is defined as 360,100,100
		# 	hue is 0 to 360 degrees on the color wheel
		#	sat is 0 to 100 percent white
		#	val is 0 to 100 percent black

		# openCV HSV is 179,255,255
		# 	255 is the max integer, so the 360 is divided by 2

		# interpolate
		# a color coordinate has 3 values
		# a color threshhold has 6 values


		# opencv hsv values are 0 to 179,255,255
		# trackbar settings are 360,100,100

		sk8_hsv = [1,360,360,100,100,100,100,1,1]
		ocv_hsv = [1,179,179,255,255,255,255,1,1]

		ocv_set = sk8math.interpolate(np.array(settings), 0,np.array(sk8_hsv), 0,np.array(ocv_hsv))
		ocv_set = ocv_set.astype(int)
		cls,hl,hu,sl,su,vl,vu,cl,cu = ocv_set

		

#		# interpolate sk8-hsv to openCV-hsv
#		hl = int(hl / 2)
#		hu = int(hu / 2)
#		sl = int((sl / self.barmax[3]) * 255)  # 0 to 100 pct
#		su = int((su / self.barmax[4]) * 255)
#		vl = int((vl / self.barmax[5]) * 255)  # 0 to 100 pct
#		vu = int((vu / self.barmax[6]) * 255)

		#lower = np.array([(settings['hue_min']/2),settings['sat_min'],settings['val_min']])
		#upper = np.array([(settings['hue_max']/2),settings['sat_max'],settings['val_max']])
		lower = np.array([hl,sl,vl])
		upper = np.array([hu,su,vu])
		imgHsv = cv.cvtColor(img,cv.COLOR_BGR2HSV)
		imgMask = cv.inRange(imgHsv,lower,upper) # choose pixels by hsv threshholds
		imgMasked = cv.bitwise_and(img,img, mask=imgMask)
	
		imgBlur = cv.GaussianBlur(imgMasked, (17, 17), 1)  # started at (7,7);  the bigger kernel size pulls together the pieces of padr
		imgGray = cv.cvtColor(imgBlur, cv.COLOR_BGR2GRAY)
	
		# canny: edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
		imgCanny = cv.Canny(imgGray, cl, cu)
	
		# dilate: thicken the line
		kernel = np.ones((5, 5))
		imgDilate = cv.dilate(imgCanny, kernel, iterations=1)

		# get a data array of polygons, one contour boundary for each object
		contours, _ = cv.findContours(imgDilate, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
		if clsdebug == cls:
			self.debugImages = [imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate]

		# get bounding box for each contour
		for contour in contours:
			area = cv.contourArea(contour)
			perimeter = cv.arcLength(contour, True)
			polygon = cv.approxPolyDP(contour, 0.02 * perimeter, True)
			l,t,w,h = cv.boundingRect(polygon)

			tl = round(l/self.imgWid, 6)
			tt = round(t/self.imgHt, 6)
			tw = round(w/self.imgWid, 6)
			th = round(h/self.imgHt, 6)

			bbox = sk8math.Bbox(tl,tt,tw,th)
			obj = DetectedObject(cls, bbox)
			objects.append(obj)
		return

	def probeDebugImages(self):
		return self.img, self.debugImages

if __name__ == '__main__':
	fname = '/home/john/sk8/bench/testcase/frame/6.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
		quit()

	visualcortex = VisualCortex()
	objs = visualcortex.detectObjects(frame)
	print(*objs, sep='\n')
