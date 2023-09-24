''' skate.py - copied from sk8/sk8.py '''

import sys
import cv2 as cv
import numpy as np
import time
import logging
import traceback
import universal as uni
import visualcortex as vc
import hippocampus as hc
import frontalcortex as fc
import drone as drn

class Sk8:
	save_nth = 1

	def __init__(self):
		self.visualcortex = None
		self.hippocampus = None
		self.frontalcortex = None
		self.neck = None
		self.drone = None
		self.timesave = 0
		self.prevframenum = 0
	
	def wakeup(self,flymode=True):
		uni.configureLogging('fly')
		logging.info('good morning')
	
		# reconstitute the brain parts
		self.visualcortex = vc.VisualCortex()
		self.hippocampus = hc.Hippocampus()
		self.frontalcortex = fc.FrontalCortex()
		self.drone = drn.Drone(flymode=flymode)
	
		if self.save_nth:
			self.dirframe = uni.makedir('frame')
			self.dirtrain = uni.makedir('train')

	def act(self):
		started = self.drone.prepareForTakeoff()
		if started:
			logging.info('start sensoryMotorCircuit')
			acting = True
			while acting:
				try:
					acting = self.sensoryMotorCircuit()
				except Exception as e:
					traceback.print_exc()
					logging.error(e)
					logging.error('error in sensoryMotorCircuit. forced landing.')
					break
			self.drone.shutdown()		
			self.drone.wait()  # block here until video and telemetry threads stopped

	def sleep(self):
		logging.info('good night')
	
	def sensoryMotorCircuit(self):
		frame,framenum = self.drone.getFrame()
		if frame is None:
			logging.info('no frame.  retry.')
			time.sleep(0.2)
			return True
		
		# check framenum, if no change, bail
		if self.prevframenum >= framenum:
			pass # logging.warning('no new frame')  # repeat previous frame
		else:
			self.prevframenum = framenum 

		objs = self.visualcortex.detectObjects(frame,vc.Detect.threshhold_seeds)
		
		fmap,posts = self.hippocampus.buildMap(objs,framenum,frame)

		vector = self.frontalcortex.navigate(self.drone.state, fmap, drn.max_mmo)

		rccmd = False
		if vector:
			rccmd = self.drone.go(vector)
	
		self.log(frame,framenum,objs,fmap,posts,rccmd)
		return (vector and rccmd)

	def log(self,frame,framenum,objs,fmap,posts,rccmd):
		if not uni.soTrue(framenum,self.save_nth) or frame is None:
			return

		# save frame
		fname = f'{self.dirframe}/{framenum}.jpg'
		cv.imwrite( fname, frame)

		# save training data
		fname = f'{self.dirtrain}/{framenum}.txt'
		f = open(fname, 'a')
		for obj in objs:
			f.write(obj.write())
		f.close()

		# save mission log
		ts = time.time()
		tsd = ts - self.timesave
		src = rccmd.replace(' ','.') if rccmd else 'rc'
		agl = fmap.agl if fmap else 0
		prefix = f"rc:{src};ts:{ts};tsd:{tsd};fn:{framenum};agl:{agl};"
		self.timesave = ts
		logging.log(logging.MISSION, prefix)

		# log posts
		posts = self.hippocampus.probePostData()
		ssave = ''
		for k in posts.keys():
			v = posts[k]
			s = f"{k.replace(' ','_')}={v}"
			ssave += s + ';'
		logging.debug(ssave)

if __name__ == '__main__':
	if len(sys.argv) < 2 or sys.argv[1] not in ['fly','nofly']:
		print ('usage: python3 sk8.py [fly nofly]')
		quit()
	flymode = True if sys.argv[1] == 'fly' else False
	sk8 = Sk8()
	sk8.wakeup(flymode=flymode)
	sk8.act()
	sk8.sleep()
'''
class Sk8

sk8.py
sk8d.sh
sk8d.service
skim.py 

todo:

A. inhibitions, prefrontal cortex

B. gradient descent training system

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

2. maneuvers
	a. hover over pad
	b. liftoff
	c. land
	d. spiral around pad

3. mirror calibration

7. orientation - see orient.py
	use cones
	three overlays: map, frame, sk8
		1. map - "basemap" centered and angled on arena, plus home
		2. frame - momentary position of tello, "base" has radius of tello as virtual pad
		3. pad - momentary position of sk8, often obscurred, temporarily fixed
	- superimpose map onto frame, frameMap matches frame by definition
	- underimpose frame under basemap

8. dead reckoning
	when orientation fails, go with previous calculations

11. photo angle correction, center vs peripheral
'''
