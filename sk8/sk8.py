''' sk8.py - class Sk8 - control sk8 robot '''

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
	save_nth = 1

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
			f.write(f"{obj.cls} {obj.bbox.l} {obj.bbox.t} {obj.bbox.w} {obj.bbox.h}\n")
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
'''
class Sk8

sk8.py
sk8d.sh
sk8d.service
skim.py 

	four items are saved to disk
		1. frames, already flipped for mirror, no resize
		2. training file, detected objects, must match frame
		3. mission log, logging level 17 only
		4. debug log, logging all levels

		Notes on data saving: 
			see universal.py for folder and filename settings
			console log does NOT display levels debug and mission.
			frames and mission log can be used to rerun a mission in the simulator.
			when flying the drone, we save frames and mission log
				when flying the simulator, we do not
			training files:
				saved automaically during flight
				can optionally be rewritten during sim
				can be rewritten one frame at a time on-demand during sim

todo:

inhibitions, prefrontal cortex

write gradient descent training system

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

10. fix rc compose to use body coordinates instead of ground coordinates

11. photo angle correction
'''
