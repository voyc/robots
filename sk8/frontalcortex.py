''' frontalcortex.py - class FrontalCortex, navigation '''

import logging
import universal as uni
import time

class FrontalCortex:
	max_mission_time = 30

	def __init__(self):
		self.state = 'bored'
		self.vector = (2,4,5,6)
		self.timestart = time.time()

	def navigate(self):
		# are we airborne?
		# are we ready for takeoff?
		if (time.time() - self.timestart) > self.max_mission_time:
			logging.info('mission clock expired.  forced landing.')
			return False
		return self.vector

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
