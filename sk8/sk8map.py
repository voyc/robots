''' sk8map.py - class Map, Spot, Pad, Cone, Arena '''

import sk8math

class Map:
	agl_k = 1153

	def __init__(self, spot, pad, cones=[], arena=[]):
		self.spot = spot
		self.pad = pad
		self.cones = cones
		self.arena = arena
		self.state = 'new'
		self.pxlpermm = 0
		self.agl = 0
		self.calc()

	def calc(self):
		# set state
		self.state = 'lost' # no pad, no spot
		if self.spot and self.calcAgl( self.spot.pxlpermm) < Spot.agl_max:
			self.state = 'spot'
		elif self.pad and self.pad.state == 'complete':
			self.state = 'pad'

		# choose pxlpermm and calc agl
		self.pxlpermm = self.spot.pxlpermm if self.state == 'spot' else self.pad.pxlpermm
		self.agl = self.calcAgl(self.pxlpermm)

	def calcAgl(self, pxlpermm):
		if pxlpermm <=0:
			return 0
		return int(Map.agl_k/pxlpermm)  # hyperbola equation y=k/x

	def __str__(self):
		s = f'pad: {self.pad.bbox}'
		s += f'\nspot: {self.spot.bbox}'
		s += f'\ncones: {len(self.cones)}'
		s += f'\nstate: {self.state}, pxlpermm: {self.pxlpermm}, agl: {self.agl}'
		return s

class Spot:
	mm_radius = 8     # spot is 16 mm diameter
	mm_offset = 46    # spot center is 46 mm forward of pad center
	agl_max = 600     # good for agl calc up to max mm

	def __init__(self, bbox, unit='pxl'):
		self.bbox = bbox
		self.pxlpermm = bbox.radius / self.mm_radius
		self.unit = unit

class Pad:
	mm_radius = 70     # pad is 14 cm square

	def __init__(self,padl,padr,state='new',unit='pxl'):
		self.padl = padl
		self.padr = padr
		self.state = state
		self.unit = unit
		self.pxlpermm = False
		self.purpose = 'frame'  # frame or home
		self.calc()


	def calc(self):
		# combine left and right halves into a single pad defined by center, angle, radius
		if self.padl and self.padr:
			self.center = sk8math.averageTwoPoints(self.padl.bbox.center, self.padr.bbox.center)
			self.angle,self.radius,self.pt3 = sk8math.triangulateTwoPoints(self.padl.bbox.center, self.padr.bbox.center)
		else:
			self.center = sk8math.Pt(0,0)
			self.angle = 0
			self.radius = 0

		# redefine as a bbox
		self.bbox = self.getBbox()

		# calc the conversion factor
		self.pxlpermm = self.radius / self.mm_radius

	def getBbox(self):
		l = self.center.x - self.radius
		t = self.center.y - self.radius
		w = self.radius
		h = self.radius
		bx = sk8math.Bbox(l,t,w,h)
		return bx

class Cone:
	radius = 40    # cone diameter is 8 cm
	radius_range = 0.40

	def __init__(self, center):
		self.center = center

class Arena:
	padding = 80
	margin = 40

	def __init__(self,bbox):
		self.bbox = bbox

'''
		# notes on vector, slope, angle, quadrant
		# [angle, radius]  = similar to a vector in that it indicates direction and distance
		# [leny, lenx]  = a slope, rise over run
		# [lenx, leny] = a vector, [2,4] means move 2 mm to the left and 4 mm up
'''
