''' sk8.py - control sk8 robot '''

import cv2 as cv
import numpy as np
import time
import logging
import universal as uni
import visualcortex as vc
import hippocampus as hc
import frontalcortex as fc
import neck as nek
import drone as drn

class Sk8:
	save_nth = 10
	logpost_nth = 10

	def yahoo(self, data, count):
		pass
	
	def __init__(self):
		self.visualcortex = None
		self.hippocampus = None
		self.frontalcortex = None
		self.neck = None
		self.drone = None
		self.timesave = 0
	
	def wakeup(self):
		uni.configureLogging('fly')
		logging.info('good morning')
	
		# reconstitute the brain parts
		self.visualcortex = vc.VisualCortex()
		self.hippocampus = hc.Hippocampus()
		self.frontalcortex = fc.FrontalCortex()
		self.neck = nek.Neck()
		self.drone = drn.Drone(self.yahoo,self.sensoryMotorCircuit)
	
		if self.save_nth:
			self.dirframe = uni.makedir('frame')
			self.dirtrain = uni.makedir('train')

	def act(self):
		started = self.drone.prepareForTakeoff()
		if started:
			logging.info('start mission')
			self.drone.wait()  # block here until video and telemetry threads stopped
	
	def sleep(self):
		logging.info('good night')
	
	def sensoryMotorCircuit(self, frame, framenum):
		objs = self.visualcortex.detectObjects(frame)
		fmap = self.hippocampus.buildMap(objs,framenum,frame)
		vector = self.frontalcortex.navigate()
		rccmd = 'rc'
		if not vector:
			self.drone.stop()
		else:
			rccmd = uni.composeRcCommand(vector)
			#self.drone.cmd.sendCommand(rccmd)
	
		self.log(frame,framenum,objs,rccmd,fmap)
		return

	def log(self,frame,framenum,objs,rccmd,fmap):
		if not uni.soTrue(framenum,self.save_nth) or frame is None:
			return

		#self.detect = self.visualcortex.probeEdgeDetection()
		#baseMap, frameMap = self.hippocampus.probeMaps()
		posts = self.hippocampus.probePostData()
		#vector = self.frontalcortex.probeVector()
		#rccmd = self.neck.probeRcCmd()

		# save frame
		fname = f'{self.dirframe}/{framenum}.jpg'
		cv.imwrite( fname, frame)

		# save training data
		fname = f'{self.dirtrain}/{framenum}.txt'
		f = open(fname, 'a')
		for obj in objs:
			f.write(f"{obj.cls} {obj.bbox.t} {obj.bbox.l} {obj.bbox.w} {obj.bbox.h}\n")
		f.close()

		# save mission log
		ts = time.time()
		tsd = ts - self.timesave
		src = rccmd.replace(' ','.')
		agl = fmap.agl
		prefix = f"rc:{src};ts:{ts};tsd:{tsd};fn:{framenum};agl:{agl};"
		self.timesave = ts
		logging.log(logging.MISSION, prefix)

		# log posts
		ssave = ''
		for k in posts.keys():
			v = posts[k]
			s = f"{k.replace(' ','_')}={v}"
			ssave += s + ';'
		logging.debug(ssave)

if __name__ == '__main__':
	sk8 = Sk8()
	sk8.wakeup()
	sk8.act()
	sk8.sleep()
