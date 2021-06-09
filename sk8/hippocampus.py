''' hippocampus.py - class Hippocampus - spatial analysis, mapping, orientation '''
import cv2 as cv
import numpy as np
import time
import logging
import os
import copy
import colorsys
import re
import universal as uni
import sk8mat as sm
import visualcortex as vc

class Hippocampus:
	def __init__(self):
		self.frameWidth  = 960
		self.frameHeight = 720
		self.ddim = [960,720]

		self.framenum = 0
		self.frameMap = False
		self.baseMap = False
		self.posts = {}
		self.timesave = time.time()

	def findSpot(self, objects):
		# make a separate list of spots
		spota = []
		for obj in objects:
			if obj.cls == uni.clsSpot:
				spota.append(obj)
		self.post('num spot', len(spota))
		if len(spota) != 1:
			return False
		objspot = spota[0]

		# from pct to pxl
		objspot.toD(self.ddim)
		spot = sm.Spot(objspot)
		self.post('spot pxl radius', spot.dbox.radius())
		self.post('spot dpmm', spot.dpmm)
		return spot

	def findHalf(self, objects, cls):
		clsname = 'left' if cls == uni.clsPadl else 'right' # for posts

		# make separate lists of halfs
		a = []
		for obj in objects:
			if obj.cls == cls:
				a.append(obj)
		self.post(f'pad {clsname}', len(a))

		if len(a) != 1:
			return False

		half = a[0]
		half.toD(self.ddim)
		return half

	def findPad(self, objects):
		# find the two halfs
		padl = self.findHalf(objects, uni.clsPadl)
		padr = self.findHalf(objects, uni.clsPadr)

		# calc pad state
		state = 'missing'
		if padl and padr:
			#if not padl.dbox.pad(8).intersects(padr.dbox.pad(8)):
			#	state = 'nonadjacent'
			if padl.dbox.touchesEdge(self.ddim) \
			  or padr.dbox.touchesEdge(self.ddim):
				state = 'partial'
			else:
				state = 'complete'
		self.post('pad state', state)

		# create pad object
		pad = sm.Pad(padl, padr, state)
		self.post('pad pxl radius', pad.radius)
		self.post('pad dpmm', pad.dpmm)

		return pad

	def findCones(self, objects, dpmm):
		# make a separate list of cones
		conea = []
		for obj in objects:
			if obj.cls == uni.clsCone:
				conea.append(obj)
		self.post('cones found', len(conea))

		cones = []
		for edge in conea:
			edge.toD(self.ddim)
			edge.toM(dpmm)
			cone = sm.Cone(edge)
			cones.append(cone)
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
 	
	def findArena(self, cones, dpmm):
		if not cones:
			return False

		# non-rotated arena, bbox from cones
		mbox = cones[0].mbox
		for cone in cones:
			mbox.unite(cone.mbox)

		mbox = mbox.pad(sm.Arena.padding)
		arena  = sm.Arena(mbox)
		arena.fromM(dpmm)
		return arena

	def buildMap(self,objects,framenum,frame=None):
		self.posts = {}
		self.objects = objects
		self.framenum = framenum
		self.frame = frame
		self.post('framenum',framenum)
		self.post('num objects', len(objects))

		spot = self.findSpot(objects)
		pad = self.findPad(objects)

		# create map object
		fmap = sm.Map(spot, pad, self.ddim)
		self.frameMap = fmap
		self.post('map state', fmap.state)
		self.post('map dpmm', fmap.dpmm)
		self.post('map agl', fmap.agl)

		if fmap.state != 'lost':
			fmap.cones = self.findCones(objects, fmap.dpmm)
			fmap.arena = self.findArena(fmap.cones, fmap.dpmm)
			
			if fmap.pad.padl:
				fmap.pad.padl.toM(fmap.dpmm)
			if fmap.pad.padr:
				fmap.pad.padr.toM(fmap.dpmm)
			fmap.pad.calc()
			if fmap.spot:
				fmap.spot.toM(fmap.dpmm)
		return fmap, self.posts

	def post(self,key,value):
		self.posts[key] = value

	def probeMaps(self):
		return self.baseMap, self.frameMap

	def probePostData(self):
		return self.posts

if __name__ == '__main__':
	uni.configureLogging()
	logging.info('test hippocampus')
	fname = '/home/john/sk8/bench/testcase/frame/6.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
		quit()

	visualcortex = vc.VisualCortex()
	objs = visualcortex.detectObjects(frame,vc.Detect.threshhold_seeds)
	print(*objs, sep='\n')
	
	hippocampus = Hippocampus()
	mapp = hippocampus.buildMap(objs, 1)	
#	logging.info(mapp)
	print(mapp)
	print(mapp.cones)
	print(isinstance(mapp.cones[0],sm.Edge))
	print(isinstance(mapp.cones[0],sm.Cone))

'''
class Hippocampus
	Public methods:
		buildMap(img,framenum,telemetry)
'''
