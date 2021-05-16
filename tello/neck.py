''' neck.py - class Neck, navigation '''

class Neck:
	def __init__(self):
		self.state = 'bored'
		self.rccmd = 'rc 41 -6 60 40'

	def goto(self, vector):
		self.rccmd = self.composeRcCmd(vector)
		return self.rccmd

	def composeRcCmd(self, vector):
		nvec = (0,0,1,20)
		rvec = (0,0,60,50)
		rccmd = sk8math.interpolate(vector, 0, nvec, 0, rvec)
		return rccmd

	def probeRcCmd(self):
		return self.rccmd
