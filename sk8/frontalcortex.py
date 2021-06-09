''' frontalcortex.py - class FrontalCortex, navigation '''

import logging
import universal as uni
import time

class FrontalCortex:
	hoverpad_height = 700  # hover 1 meter above pad
	max_lost = 20

	def __init__(self, max_mission_time=20):
		self.max_mission_time = max_mission_time
		self.state = 'bored'
		self.vector = [0,0,0,0]
		self.timestart = 0.
		self.lostn = 0

	def navigate(self, state, fmap, max_mmo):
		# thats long enough		
		if not self.timestart:
			self.timestart = time.time()
		elif (time.time() - self.timestart) > self.max_mission_time:
			logging.info('mission clock expired.  forced landing.')
			return False

		# get location of pad
		px,py,pw = fmap.loc()
		if px < 0:
			self.vector = [0,0,0,0]
			self.lostn += 1
			if self.lostn > self.max_lost:
				logging.info('pad lost. forced landing.')
				return False 
			else:
				return self.vector
		self.lostn = 0

		# yaw
		if pw > 180:
			pw = 360 - pw
		else:
			pw = 0 - pw

		# know that current location of drone is center
		dx,dy = fmap.ctr()
		dz = fmap.agl

		# vector to desired location
		x = px - dx
		y = dy - py
		z = self.hoverpad_height - dz
		w = pw 
		ovec = [x,y,z,w]

		#if any(abs(i) > max_mmo for i in ovec): # too far off course, bail
		#	logging.warning('off course.  forced landing.')
		#	return False

		self.vector = ovec
		return ovec

	def probeVector(self):
		return self.vector
'''
class FrontalCortex:
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

This article compares Hippocampus and Prefrontal Cortex.
https://www.sciencenewsforstudents.org/article/two-brain-areas-team-make-mental-maps 

What is the difference between frontal and prefrontal cortex?

prefrontal cortex is associated with inhibition
'''
