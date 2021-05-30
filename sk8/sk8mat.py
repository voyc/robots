''' sk8mat.py - math, geometry, bounding box, and mapping functions for sk8 '''

import numpy as np

# a point is represented by a tuple, (x,y)

# a vector is represented by a list, [w,h]

def interpolate(x, b, e, bp, ep):
	# x: input value
	# b,e: begin and end of input range
	# bp,ep: begin and end of output range
	#return  int((x / (e-b)) * (ep-bp))
	return  (x / (e-b)) * (ep-bp)

def averageTwoPoints(pt1, pt2):
	data = [pt1, pt2]
	average = [sum(x)/len(x) for x in zip(*data)]
	average = tuple(np.array(average).astype(int))
	return average

def triangulateTwoPoints(ptleft, ptright):
	# length of hypotenuse
	lenx = abs(ptright[0] - ptleft[0])
	leny = abs(ptright[1] - ptleft[1])
	hypotenuse = np.sqrt(lenx**2 + leny**2)

	# point of right angle
	ptr = (ptleft[0], ptright[1])

	quadrant = quadrantPoints(ptleft,ptright)

	# angle of the hypotenuse to the vertical axis
	# see https://www.geogebra.org/classic/h6pgbftp  # sketch of quadrant upper left
	if quadrant == 'upper right' or quadrant == 'lower left':
		oa = leny/lenx if (lenx != 0) else 0 # tangent of angle = opposite over adjacent 
	else:
		oa = lenx/leny if (leny != 0) else 0 # tangent of angle = opposite over adjacent 
	radians = np.arctan(oa)
	degrs = np.degrees(radians)

	if quadrant == 'lower right':
		degrs += 90
	elif quadrant == 'lower left':
		degrs += 180
	elif quadrant == 'upper left':
		degrs += 270
	return degrs, hypotenuse, ptr
	
def quadrantAngle(angle):
	# return the quadrant of a given angle
	quadrant = ''
	if angle >= 0 and angle < 90:
		quadrant = 'upper right'
	elif angle >= 90 and angle < 180:
		quadrant = 'lower right'
	elif angle >= 180 and angle < 270:
		quadrant = 'lower left'
	elif angle >= 270 and angle <= 360:
		quadrant = 'upper left'
	return quadrant

def quadrantPoints(ptleft, ptright):
	# return the quadrant of an angle given two points
	leftx,lefty = ptleft
	rightx,righty = ptright
	quadrant = ''
	if leftx < rightx and lefty < righty:
		quadrant = 'upper right'
	elif leftx < rightx and lefty > righty:
		quadrant = 'upper left'
	elif leftx > rightx and lefty < righty:
		quadrant = 'lower right'
	elif leftx > rightx and lefty > righty:
		quadrant = 'lower left'
	return quadrant

def calcLine(c,r,a):
	# return the two endpoints of a line, given centerpoint, radius, and angle
	x,y = c
	lenh = r # length of hypotenuse
	angle = np.radians(a)
	                                   # soh cah toa
	leno = round(np.sin(angle) * lenh) # opposite: sine(angle = opposite/hypotenuse)
	lena = round(np.cos(angle) * lenh) # adjacent: cos(angle = adjacent/hypotenuse)

	x1 = x + leno
	y1 = y - lena
	x2 = x - leno
	y2 = y + lena
	return (x1,y1), (x2,y2) 

class Box:
	prec = 6

	def __init__(self, lt, wh):
		self.lt = lt  # point (tuple)
		self.wh = wh  # vector [list]
	def area(self): return self.wh[0] * self.wh[1]
	def ctr(self): return tuple((np.array(self.lt) + (np.array(self.wh) * .5)).astype(int))
	def diameter(self): return np.average(self.wh).astype(int)
	def radius(self): return int(self.diameter() / 2)
	def rb(self): return tuple(np.array(self.lt) + np.array(self.wh))
	def lt_rb(self): return (self.lt, self.rb())
	def ltrb(self): return self.lt[0], self.lt[1], self.rb()[0], self.rb()[1]
	def ltwh(self): return self.lt[0], self.lt[1], self.wh[0], self.wh[1]

	def xcalc(self):
		self.pxl_wh =  tuple(np.array(self.pxl_rb) - np.array(self.pxl_lt))

	def intersection(self, box2):
		l1,t1,r1,b1 = self.ltrb()
		l2,t2,r2,b2 = box2.ltrb()
		lenx = max(0, min(r1, r2) - max(l1, l2))
		leny = max(0, min(b1, b2) - max(t1, t2))
		return lenx * leny

	def intersects(self, box2):
		return self.intersection(box2) > 0

	def touchesEdge(self, dim):
		w,h = dim
		l,t,r,b = self.ltrb()
		touches = False
		if l <= 1 or r >= w-2 \
		or t <= 1 or b >= h-2: 
			touches = True
		return touches

	def pad(self, padding):  # previously expand
		v = np.array([padding,padding])
		self.lt = tuple(np.array(self.lt) - v)
		self.wh = self.wh = tuple(np.array(self.lt) - (v*2))

	def unite(self, box2):  # previously enlarge
		l = min(self.lt[0], box2.lt[0])
		t = min(self.lt[1], box2.lt[1])
		w = min(self.wh[0], box2.wh[0])
		h = min(self.wh[1], box2.wh[1])
		self.lt = (l,t)
		self.wh = [w,h]

	def __str__(self):
		#return f'{np.round(np.array(self.lt),self.prec)}, {np.round(np.array(self.wh),self.prec)}'
		return f'{self.lt}, {self.wh}'

def toD(p,ddim):
	return (np.array(p) * np.array(ddim)).astype(int)

def fromD(p,ddim):
	return np.array(p) / np.array(ddim)

def toM(d,dpmm):
	return np.array(d) * np.array(dpmm)

def fromM(d,dpmm):
	return tuple((np.array(d) / dpmm).astype(int))

class Edge: # represents a detected object, classification plus bounding box, in three units
	def __init__(self, cls, box=None):
		self.cls = cls
		self.pbox = box    # Box in pct
		self.dbox = None   # Box in dots (pixels)
		self.mbox = None   # Box in mm

	def fromD(self,ddim):
		lt = tuple(fromD(self.dbox.lt, ddim))
		wh = list(fromD(self.dbox.wh, ddim))
		self.pbox = Box(lt,wh)

	def toD(self,ddim):
		lt = tuple(toD(self.pbox.lt, ddim))
		wh = list(toD(self.pbox.wh, ddim))
		self.dbox = Box(lt,wh)

	def toM(self,dpmm):
		lt = toM(self.dbox.lt, dpmm)
		wh = toM(self.dbox.wh, dpmm)
		self.mbox = Box(lt,wh)

	def __str__(self):
		s = f'{self.cls}: {self.pbox}'
		if self.dbox is not None:
			s += f'; {self.dbox}'
		if self.mbox is not None:
			s += f'; {self.mbox}'
		return s

	def write(self):  # write to training data file
		l,t = self.pbox.lt
		w,h = self.pbox.wh
		s  = f'{self.cls} {l} {t} {w} {h}'
		return s

class Spot(Edge):
	mm_radius = 8     # spot is 16 mm diameter
	mm_offset = 46    # spot center is 46 mm forward of pad center
	agl_max = 600     # good for agl calc up to max mm

	def __init__(self, edge):
		self.cls = edge.cls
		self.pbox = edge.pbox
		self.dbox = edge.dbox
		self.mbox = edge.mbox
		self.dpmm = self.dbox.radius() / self.mm_radius

class Pad():
	mm_radius = 70     # pad is 14 cm square

	def __init__(self,padl,padr,state='new'):
		self.padl = padl
		self.padr = padr
		self.state = state
		self.dpmm = False
		self.purpose = 'frame'  # frame or home
		self.calc()

	def calc(self):
		# combine left and right halves into a single pad defined by center, angle, radius
		if self.padl and self.padr:
			self.center = averageTwoPoints(self.padl.dbox.ctr(), self.padr.dbox.ctr())
			self.angle,self.radius,self.pt3 = triangulateTwoPoints(self.padl.dbox.ctr(), self.padr.dbox.ctr())
		else:
			self.center = (0,0)
			self.angle = 0
			self.radius = 0

		# redefine as a bbox
		#self.bbox = self.getBbox()

		# calc the conversion factor
		self.dpmm = self.radius / self.mm_radius

	#def getBbox(self):
	#	l = self.center.x - self.radius
	#	t = self.center.y - self.radius
	#	w = self.radius
	#	h = self.radius
	#	bx = sk8math.Bbox(l,t,w,h)
	#	return bx
	
	def __str__(self):
		s = f'{self.center}, {self.angle}, {self.radius}, {self.dpmm}'
		return s

class Cone(Edge):
	radius = 40    # cone diameter is 8 cm
	radius_range = 0.40

	def __init__(self, edge):
		self.cls = edge.cls
		self.pbox = edge.pbox
		self.dbox = edge.dbox
		self.mbox = edge.mbox
		self.center = averageTwoPoints(self.dbox.lt, self.dbox.rb())

	def __str__(self):
		return f'cone {self.center}, {self.mbox.radius()}' 

class Arena():
	padding = 80
	margin = 40

	def __init__(self,mbox):
		self.mbox = mbox
		self.dbox = None

	def fromM(self,dpmm):
		lt = fromM(self.mbox.lt, dpmm)
		wh = fromM(self.mbox.wh, dpmm)
		self.dbox = Box(lt,wh)

	def __str__(self):
		return f'arena {self.mbox}' 

class Map:
	agl_k = 1153

	def __init__(self, spot, pad, cones=[], arena=None):
		self.spot = spot
		self.pad = pad
		self.cones = cones
		self.arena = arena
		self.state = 'new'
		self.dpmm = 0
		self.agl = 0
		self.calc()

	def calc(self):
		# set state
		self.state = 'lost' # no pad, no spot
		if self.spot and self.calcAgl( self.spot.dpmm) < Spot.agl_max:
			self.state = 'spot'
		elif self.pad and self.pad.state == 'complete':
			self.state = 'pad'

		# choose dpmm and calc agl
		self.dpmm = self.spot.dpmm if self.state == 'spot' else self.pad.dpmm
		self.agl = self.calcAgl(self.dpmm)

	def calcAgl(self, dpmm):
		if dpmm <=0:
			return 0
		return int(Map.agl_k/dpmm)  # hyperbola equation y=k/x

	def __str__(self):
		s = f'pad: {self.pad.center}'
		s += f'\nspot: {self.spot.mbox}'
		s += f'\ncones: {len(self.cones)}'
		s += f'\nstate: {self.state}, dpmm: {self.dpmm}, agl: {self.agl}'
		return s

if __name__ == '__main__':
	a = (1,2)
	b = (5,6)
	avg = averageTwoPoints(a, b)
	print(a, b, avg)

	c = (10,20)
	d = (40,60)
	avg = averageTwoPoints(c, d)
	print(c, d, avg)

	degrs, hypotenuse, ptr = triangulateTwoPoints(a, b)
	print(degrs, hypotenuse, ptr)

	qa = quadrantAngle(degrs)
	print(qa)

	qp = quadrantPoints(a,b)
	print(qp)

	c,d = calcLine((20,30), 10, 45)
	print(c,d)

	bb = Box((50,60), [100,90])
	print(f'ctr:  {bb.ctr()}')
	print(f'rb:   {bb.rb()}')
	print(f'ltrb: {bb.ltrb()}')
	print(f'diameter: {bb.diameter()}')
	print(f'radius:   {bb.radius()}')

	ba = Box((150,160), [200,190])
	intersection = ba.intersection(bb)
	intersect = ba.intersects(bb)
	print(intersect)

	bc = Box((100,100),(700,600))
	touch = ba.touchesEdge([640,480])
	print(touch)
	touch = bc.touchesEdge([640,480])
	print(touch)

	print(ba)
	ba.pad(5)
	print(ba)

	ba.unite(bb)
	print(ba)

	sk8_hsv     = np.array([360,360,100,100,100,100,1,1])
	ocv_hsv     = np.array([179,179,255,255,255,255,1,1])
	threshholds = np.array([ 45,135, 50, 75, 10, 25,1,1])
	ocv_set = interpolate(threshholds, 0,sk8_hsv, 0,ocv_hsv)
	print(ocv_set)

	ed = Edge(1,Box((.10,.10),[.50,.60]))
	print(ed)
	ed.toD([960,720])
	print(ed)
	ed.toM(5.4)
	print(ed)

	spot = Spot(ed)
	print(spot)
	print(spot.dpmm)

	padl = Edge(1,Box((.30,.40),[.20,.20]))
	padl.toD([960,720])
	padl.toM(5.4)
	padr = Edge(2,Box((.50,.40),[.20,.20]))
	padr.toD([960,720])
	padr.toM(5.4)
	pad = Pad(padl,padr)
	print(pad)

	ed = Edge(0,Box((.50,.40),[.20,.20]))
	ed.toD([960,720])
	ed.toM(5.4)
	cone = Cone(ed)
	print(cone)

	box = Box((20,15), [900,700])
	arena = Arena(box)
	print(arena)

	basemap = Map( spot, pad, [cone,], arena)
	print(basemap)

'''
notes on aerial photography

scale   dpmm     agl
1:1      5.4    200mm

scale of 1:1 means 1mm in the photo represents 1 mm on the ground
typical small scale is 1:100 (small scale => small area)
typical large scale is 1:240,000 (1in:3.8mi)  (large scale => large area)
scale is determined by focal length and agl of the camera, and is dependent on the printer resolution
sk8 does not use scale; we describe it here as a curiosity

the tello camera takes photos at 960 x 720, a 4:3 ratio
a 13in screen is roughly 355 x 200 mm, a 16:9 ratio
 
a 13in screen 200 mm high and 1080 pixels high has a dpmm of 5.4 (137 dpi)
at an agl of 200 mm, the frame shows a 355 x 200 mm area, so scale is 1:1
'''
