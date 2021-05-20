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
	logpost_nth = 10

	def __init__(self, save_mission=False):
		self.save_mission = save_mission
		self.frameWidth  = 960
		self.frameHeight = 720

#		self.framenum = 0
		self.frameMap = False
		self.baseMap = False
#		self.ovec = False  # orienting vector
		self.posts = {}
		self.timesave = time.time()

	def findSpot(self, objects):
		# make a separate list of spots
		spota = []
		for obj in objects:
			if obj.cls == uni.clsSpot:
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
		clsname = 'left' if cls == uni.clsPadl else 'right' # for posts

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
			pass #logging.debug(f'missing half {clsname}')

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
		padl, padlmax = self.findHalf(objects, uni.clsPadl)
		padr, padrmax = self.findHalf(objects, uni.clsPadr)

		# the two halfs are expected to intersect (unless perfectly straight up)
		if padl and padr and not padl.bbox.intersects( padr.bbox):
			pass #logging.debug('pad halves do not intersect')

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
			if obj.cls == uni.clsCone:
				conea.append(obj)
		self.post('cones found', len(conea))

		# choose only correctly sized objects
		radmin = sk8map.Cone.radius - (sk8map.Cone.radius_range*sk8map.Cone.radius)
		radmax = sk8map.Cone.radius + (sk8map.Cone.radius_range*sk8map.Cone.radius)
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
				obj.cls = uni.clsNone
		self.post('cones accepted', len(cones))

		# go back and scrub objects list
		for obj in conea:
			if obj.cls == uni.clsNone:
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
		bbox.expand(sk8map.Arena.padding)
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
		if self.save_mission:
			self.dirframe = uni.makedir('frame')
			self.dirtrain = uni.makedir('train')

		#self.visualcortex = visualcortex.VisualCortex()
 
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

		if uni.soTrue(framenum, self.logpost_nth):
			self.logPosts()
		self.frameMap = fmap
		return fmap
	
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

	def logPosts(self):
		ssave = ''
		for k in self.posts.keys():
			v = self.posts[k]
			s = f"{k.replace(' ','_')}={v}"
			ssave += s + ';'
		logging.debug(ssave)
	
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
	logging.info(*objs, sep='\n')
	
	hippocampus = Hippocampus()
	hippocampus.start()
	mapp = hippocampus.buildMap(objs, 1)	
	logging.info(mapp)
	logging.info(*objs, sep='\n')

'''
aircraft altitude is measured in multiple ways
   agl - above ground level
   msl - mean sea level, based on 19-year averages
   barometric pressure, varies depending on the weather

baro reported by the tello is assumed to be MSL in meters to two decimal places
   a typical value before flying is 322.32
   the elevation of Chiang Mai is 310 meters

before takeoff, the camera is 20mm above the pad

all of our internal calculations are in mm
'''
