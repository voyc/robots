''' hippocamapus.py - class Hippocampus - spatial analysis, mapping, orientation '''
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
import sk8map

class Hippocampus:
	def __init__(self, ui=False, save_mission=False):
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

	def findSpot(self, objects):
		# make a separate list of spots
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
			if obj.bbox.radius > objspot.bbox.radius:
				objspot = obj

		# go back and scrub objects list
		for obj in spota:
			if obj is not objspot:
				objects.remove(obj)

		# from pct to pxl
		bbox = copy.deepcopy(objspot.bbox)
		bbox.l *= self.frameWidth
		bbox.t *= self.frameHeight
		bbox.w *= self.frameWidth 
		bbox.h *= self.frameHeight 
		bbox.calc()  # calc center, radius

		spot = sk8map.Spot(bbox)
		self.post('spot pxl diam', spot.bbox.diameter)
		self.post('spot pxlpermm', spot.pxlpermm)
		return spot

	def findHalf(self, objects, cls):
		clsname = 'left' if cls == self.clsPadl else 'right' # for posts

		# make separate lists of halfs
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
		# find the two halfs
		padl, padlmax = self.findHalf(objects, self.clsPadl)
		padr, padrmax = self.findHalf(objects, self.clsPadr)

		# the two halfs are expected to intersect (unless perfectly straight up)
		if padl and padr and not padl.bbox.intersects( padr.bbox):
			logging.debug('pad halves do not intersect')

		# replicate missing half
		if padl and not padr:
			#logging.warning('generate padr')
			padr = copy.deepcopy(padl)
			padr.bbox.l += (padr.bbox.w)
			padr.bbox.calc()
		if padr and not padl:
			#logging.warning('generate padl')
			padl = copy.deepcopy(padr)
			padl.bbox.l -= (padl.bbox.w)
			padl.bbox.calc()

		# calc pad state
		state = 'missing'
		if padl and padr:
			if padl.bbox.touchesEdge(self.frameWidth,self.frameHeight) \
			or padr.bbox.touchesEdge(self.frameWidth,self.frameHeight):
				state = 'partial'
			else:
				state = 'complete'
		self.post('pad state', state)

		# create pad object
		pad = sk8map.Pad(padl, padr, state)
		self.post('pad pxl diam', pad.bbox.diameter)
		self.post('pad pxlpermm', pad.pxlpermm)

		return pad

	def findCones(self, objects, pxlpermm):
		# make a separate list of cones
		conea = []
		for obj in objects:
			if obj.cls == self.clsCone:
				conea.append(obj)
		self.post('cones found', len(conea))

		# choose only correctly sized objects
		radmin = self.cone_radius - (self.cone_radius_range*self.cone_radius)
		radmax = self.cone_radius + (self.cone_radius_range*self.cone_radius)
		cones = []
		for obj in conea:
			# from pct to pxl
			cone = copy.deepcopy(obj)  # original object stays in unit pct
			cone.bbox.l *= self.frameWidth
			cone.bbox.t *= self.frameHeight
			cone.bbox.w *= self.frameWidth 
			cone.bbox.h *= self.frameHeight 

			# from pxl to mm
			cone.bbox.tomm(pxlpermm)
			if cone.bbox.radius > radmin and cone.bbox.radius < radmax:
				cones.append(cone)
			else:
				obj.cls = self.clsNone
		self.post('cones accepted', len(cones))

		# go back and scrub objects list
		for obj in conea:
			if obj.cls == self.clsNone:
				objects.remove(obj)

		#if len(cones) <= 0:
		#	cones = False
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
		arena  = sk8map.Arena(bbox)
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
#			self.openUI()
			logging.info('UI opened')
		if self.save_mission:
			self.dirframe = uni.makedir('frame')
			self.dirtrain = uni.makedir('train')

		#self.visualcortex = visualcortex.VisualCortex()
 
	def stop(self):
		logging.info('hippocampus stopping')
		if self.ui:
			self.closeUI()

	def buildMap(self,objects,framenum):
		self.post('framenum',framenum)
		spot = self.findSpot(objects)
		pad = self.findPad(objects)

		# create map object
		fmap = sk8map.Map(spot, pad)
		self.post('map state', fmap.state)
		self.post('map pxlpermm', fmap.pxlpermm)
		self.post('map agl', fmap.agl)

		if fmap.state != 'lost':
			fmap.cones = self.findCones(objects, fmap.pxlpermm)
			fmap.arena = self.findArena(fmap.cones)
			
			if fmap.pad.padl:
				fmap.pad.padl.bbox.tomm(fmap.pxlpermm)
			if fmap.pad.padr:
				fmap.pad.padr.bbox.tomm(fmap.pxlpermm)
			fmap.pad.calc()
			if fmap.spot:
				fmap.spot.bbox.tomm(fmap.pxlpermm)

		self.frameMap = fmap
		return fmap
	
	def processFrame(self, img, framenum, objs, teldata=None):
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
			pass

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
		if self.ui:
			portal.drawUI()

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

	def post(self,key,value):
		self.posts[key] = value
		s = f'{key}={value}'
		logging.debug(s)
	
	def probeMaps(self):
		return self.baseMap, self.frameMap

	def probePostData(self):
		return self.posts

if __name__ == '__main__':
	from visualcortex import VisualCortex
	fname = '/home/john/sk8/bench/testcase/frame/6.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
		quit()

	visualcortex = VisualCortex()
	objs = visualcortex.detectObjects(frame)
	print(*objs, sep='\n')
	
	hippocampus = Hippocampus()
	hippocampus.start()
	mapp = hippocampus.buildMap(objs)	
	#hippocampus.processFrame(objs,1,None)
	hippocampus.stop()


	print(mapp)
	print(*objs, sep='\n')
	
