'''
hippocamapus.py - class Hippocampus - object detection by color and contour using computer vision

Public methods:
	#processFrame(img,framenum,telemetry)
		detectObjects - visual cortex, pareital lobe, occipital lobe, Brodmann area
		buildMap - hippocampus, retrosplenial cortex
	drawUI()
'''

import cv2 as cv
import numpy as np
from datetime import datetime
import logging
import os
import copy
import colorsys
import universal

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
	# return the quadrant of a given angle
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
	# return the quadrant of an angle given two points
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
	# return the two endpoints of a line, given centerpoint, radius, and angle
	x,y = c
	lenh = r # length of hypotenuse
	angle = np.radians(a)
	                                   # soh cah toa
	leno = round(np.sin(angle) * lenh) # opposite: sine(angle = opposite/hypotenuse)
	lena = round(np.cos(angle) * lenh) # adjacent: cos(angle = adjacent/hypotenuse)

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
	# bbox is defined by an l-t point and a w-h vector, this is what NN data uses
	# redefined with b,r, center, diameter, radius
	def __init__(self, l,t,w,h):
		self.l = l
		self.t = t
		self.w = w
		self.h = h
		self.calc()

	def calc(self):
		# bottom right is a point
		# center is a point
		self.r = self.l + self.w
		self.b = self.t + self.h
		self.center = Pt(self.l+round(self.w/2,6), self.t+round(self.h/2,6))
		self.diameter = (self.w+self.h)/2
		self.radius = self.diameter/2

	def intersects(self, box2):
		if ((self.l > box2.l and self.l < box2.r) or (self.r > box2.l and self.r < box2.r)) \
		and ((self.t > box2.t and self.t < box2.b) or (self.b > box2.t and self.b < box2.b)): 
			return True
		else:
			return False

	def touchesEdge(self, frameWidth, frameHeight):
		touches = False
		if self.l <= 1 or self.r >= frameWidth-2 \
		or self.t <= 1 or self.b >= frameHeight-2: 
			touches = True
		return touches

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
	def __init__(self, pad, cones, arena, home=False):
		self.pad = pad
		self.cones = cones
		self.arena = arena
		self.home = home 

class Hippocampus:
	def __init__(self, ui=True, saveTrain=False):
		self.ui = ui
		self.saveTrain = saveTrain

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

		self.frameWidth  = 640   # 960
		self.frameHeight = 480   # 720
		self.frameDepth  = 3

		self.datalineheight = 22
		self.datalinemargin = 5

		self.useNeuralNet = False

		self.process_frame_nth = 1 #6 # fps is normally 33, we process 5 per second
		self.save_post_nth = 1
		self.save_train_nth = 1
		self.save_frame_nth = 1

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
		              ( self.clsPadr, 283,320,  24, 76,  30, 85,  82,127 ),
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
		if self.framenum % self.save_post_nth == 0:
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
		#cls,hl,hu,sl,su,vl,vu,_,_ = settings
		#hl /= self.barmax['hue_min']  # 0 to 360 degrees
		#hu /= self.barmax['hue_max']
		#sl /= self.barmax['sat_min']  # 0 to 100 pct
		#su /= self.barmax['sat_max']
		#vl /= self.barmax['val_min']  # 0 to 100 pct
		#vu /= self.barmax['val_max']

		# colorsys values are all 0.0 to 1.0
		rl,gl,bl = colorsys.hsv_to_rgb(hl,sl,vl)
		ru,gu,bu = colorsys.hsv_to_rgb(hu,su,vu)

		# RBG and BGR valus are 0 to 255; convert from 0 to 1
		rl *= 255
		ru *= 255
		gl *= 255
		gu *= 255
		bl *= 255
		bu *= 255
		colormin = bl,gl,rl
		colormax = bu,gu,ru

		# BGR values for hue only
		hrl,hgl,hbl = colorsys.hsv_to_rgb(hl,1.0,1.0)
		hru,hgu,hbu = colorsys.hsv_to_rgb(hu,1.0,1.0)
		hrl *= 255
		hru *= 255
		hgl *= 255
		hgu *= 255
		hbl *= 255
		hbu *= 255
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
		if self.framenum % self.process_frame_nth:
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
			imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = self.debugImages
			imgHsv= cv.cvtColor( imgHsv, cv.COLOR_HSV2BGR)
			#imgTuple = ([imgPost,self.imgColor,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal])
			#imgTuple = ([imgPost,self.imgColor,imgMasked],[imgMap,imgFinal,imgCanny])
			imgTuple = ([imgPost,imgMask,imgMasked],[imgMap,imgFinal,imgCanny])
		stack = self.stackImages(1.0,imgTuple)

		# show
		cv.imshow('Image Processing', stack)

	#
	# end UI section, begin image processing section
	#

	def detectObjectsNN(self,img):
		pass

	def detectObjectsCV(self,img):
		objects = []
		self.detectContours(img, self.obj_settings[self.clsCone], objects)
		self.detectContours(img, self.obj_settings[self.clsPadl], objects)
		self.detectContours(img, self.obj_settings[self.clsPadr], objects)
		self.detectContours(img, self.obj_settings[self.clsSpot], objects)
		return objects

	def detectContours(self,img,settings,objects):
		# draw a one-pixel black border around the whole image
		#	when the drone is on the pad, 
		#	each halfpad object extends past the image boundary on three sides, 
		#	and findContours detects only the remaining edge as an object
		cv.rectangle(img, (0,0), (self.frameWidth-1,self.frameHeight-1), (0,0,0), 1)

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

		cls,hl,hu,sl,su,vl,vu,cl,cu = settings
		hl = int(hl / 2)
		hu = int(hu / 2)
		sl = int((sl / self.barmax[3]) * 255)  # 0 to 100 pct
		su = int((su / self.barmax[4]) * 255)
		vl = int((vl / self.barmax[5]) * 255)  # 0 to 100 pct
		vu = int((vu / self.barmax[6]) * 255)

		#lower = np.array([(settings['hue_min']/2),settings['sat_min'],settings['val_min']])
		#upper = np.array([(settings['hue_max']/2),settings['sat_max'],settings['val_max']])
		lower = np.array([hl,sl,vl])
		upper = np.array([hu,su,vu])
		imgHsv = cv.cvtColor(img,cv.COLOR_BGR2HSV)
		imgMask = cv.inRange(imgHsv,lower,upper) # choose pixels by hsv threshholds
		imgMasked = cv.bitwise_and(img,img, mask=imgMask)
	
		imgBlur = cv.GaussianBlur(imgMasked, (7, 7), 1)
		imgGray = cv.cvtColor(imgBlur, cv.COLOR_BGR2GRAY)
	
		# canny: edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
		imgCanny = cv.Canny(imgGray, cl, cu)
	
		# dilate: thicken the line
		kernel = np.ones((5, 5))
		imgDilate = cv.dilate(imgCanny, kernel, iterations=1)

		# get a data array of polygons, one contour boundary for each object
		contours, _ = cv.findContours(imgDilate, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
		if self.clsdebug == cls:
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
			obj = DetectedObject(cls, bbox)
			objects.append(obj)
		return

	def findSpot(self, objects, pad):
		spota = []
		for obj in objects:
			if obj.cls == self.clsSpot:
				spota.append(obj)

		self.post('num spot', len(spota))
		if len(spota) <= 0:
			logging.warning('missing spot')
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
		if len(a) >= 1:
			o = a[0]
		else:
			logging.debug(f'missing half {clsname}')

		# if multiples, choose the one with the largest radius 
		if len(a) > 1:
			for obj in a:
				if obj.bbox.radius > o.bbox.radius:
					o = obj

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
		return half

	def findPad(self, objects):
		padl = self.findHalf(objects, self.clsPadl)
		padr = self.findHalf(objects, self.clsPadr)

		# padr and padl are expected to intersect (unless perfectly straight up)
		if padl and padr and not padl.bbox.intersects( padr.bbox):
			logging.debug('pad halves do not intersect')

		if padl and not padr:
			padr = copy.deepcopy(padl)
			padr.bbox.l += (padr.bbox.w * 2)
			padr.bbox.calc()
		if padr and not padl:
			padl = copy.deepcopy(padr)
			padl.bbox.l -= (padl.bbox.w * 2)
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

		# using pad or spot
		if pad.half_state == 'complete':
			pad.state = 'pad'
		elif spot:
			pad.state = 'spot'
		elif pad.half_state == 'partial':
			pad.state = 'pad'
		else:
			pad.state = 'missing' # no pad, no spot
		self.post('pad state', pad.state)

		# calc conversion factor 
		if pad.state == 'pad':
			pad.calc()
			self.pxlpermm = pad.radius / self.pad_radius
		elif pad.state == 'spot':
			self.pxlpermm = spot.pxlpermm
		if self.pxlpermm == 0.0:		
			pad.state = 'missing'

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

	def matchMap(data):
		pass
	
	def saveTrainingData(self,img,objects):
		if self.saveTrain and self.framenum % self.save_train_nth == 0:
			ht = 0
			fname = f'{self.outdir}/sk8_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}_ht_{ht}'
			txtname = f'{fname}.txt'
			f = open(txtname, 'a')

			for obj in objects:
				f.write(f"{obj.cls} {obj.bbox.t} {obj.bbox.l} {obj.bbox.w} {obj.bbox.h}\n")
			f.close()

	def start(self):
		logging.info('hippocampus starting')
		if self.ui:
			self.openUI()
			logging.info('UI opened')

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
	
	def processFrame(self,img, framenum, teldata):
		self.framenum += 1
		ovec = False
		rccmd = 'rc 0 0 0 0'

		if self.framenum % self.process_frame_nth: 
			return ovec,rccmd

		self.post('input frame num', framenum)
		self.post('frame num', self.framenum)

		# reduce dimensions from 960x720 to 640x480
		img = cv.resize(img, (self.frameWidth, self.frameHeight))

		# flip vertically to correct for mirror
		img = cv.flip(img, 0) # 0:vertically
		
		self.imgPrep = img # save for use by drawUI

		# get settings from trackbars
		if self.ui:
			self.readSettings()

		# detect objects - unit: percent of frame
		self.objects = self.detectObjects(img)
		self.post('objects found',len(self.objects))

		# build map
		self.frameMap = self.buildMap(self.objects)
		if not self.frameMap:
			return ovec,rccmd

		if teldata:
			agl = teldata['agl'] if teldata else 0
			perspot = self.frameMap.spot.pxlpermm
			perpad = self.frameMap.pad.pxlpermm
			logging.debug(f'pxlpermm:{self.pxlpermm} spot:{perspot}, pad:{perpad}, agl:{agl}')

		# first time, save base  ??? periodically make new base
		#if True: #not self.baseMap:
		if self.pxlpermm > 0.0:
				
			pxlpermm_at_1_meter = 0.7300079591720976
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
			
			ovec = np.array(self.frameMap.pad.center.tuple()) - np.array(self.baseMap.pad.center.tuple())
			diffx,diffy = ovec
			ovec = (diffx, diffy, 0, 0)

		# compare pad angle and radius between basemap and framemap
		# use this to reorient frame to map
		# rotate basemap and draw on top of frame image
		# rotate framemap and frameimg and draw underneath basemap

		# save image and objects for mission debriefing and neural net training
		self.saveTrainingData(img, self.objects)

		if ovec:
			rccmd = universal.composeRcCommand(ovec)
			self.post('nav cmd', rccmd)

		# display through portal to human observer
		self.drawUI()

		return ovec,rccmd

if __name__ == '__main__':
	# run a drone simulator
	universal.configureLogging()
	logging.debug('')
	logging.debug('')

	dirframe = '/home/john/sk8/bench/frame'
	framenum = 1

	hippocampus = Hippocampus(ui=True, saveTrain=False)
	hippocampus.start()

	while True:
		fname = f'{dirframe}/{framenum}.jpg'
		frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
		if frame is None:
			logging.error(f'file not found: {fname}')
			break;

		ovec = hippocampus.processFrame(frame, framenum, None)

		# kill switch
		k = cv.waitKey(1)  # in milliseconds, must be integer
		if k & 0xFF == ord('n'):
			framenum += 1
			continue
		elif k & 0xFF == ord('p'):
			framenum -= 1
			continue
		elif k & 0xFF == ord('r'):
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
todo

1. benchmark flight(s), manual
	a. drift to all four quadrants
	b. ground to 2 meters
	c. rotation to four quadrants

2. incorporate land cmd

2. execute rc command, to hover over pad

e. mirror calibration

future:
	home position: as inverted copy of initial pad, in fixed position to arena 
	sk8 position: pad surrounded by oval.

temporary:
	pad position, fixed

basemap: centered, angled, and framed on arena, plus home
	fit arena to rotated rect

x superimpose map onto frame, frameMap matches frame by definition

underimpose frame under basemap
	match frame to map  (3 cones, 2 cones, whatever, which line up?)

convert Pt to tuple
	use tuple for point and list for vector
	use np.array() for matrix math among points and vectors
	all points are 2D, except for the drone position, which is 3D
		the 4th D could be yaw angle

test cases
	angle of pad, 4 quadrants
	on the ground
	missing left
	missing right
	missing cones
	missing left, right, cones

dead reckoning
	when pad and arena is lost
	go with previous calculations

are we airborne?  do we use takeoff?

when the drone is on the pad, how is the radius calculated?
'''
