''' frontalcortex.py - class FrontalCortex, navigation '''

import logging
import universal as uni
import time

class FrontalCortex:
	max_mission_time = 20

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
