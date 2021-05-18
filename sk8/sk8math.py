''' sk8math.py - math and geometry functions '''
import numpy as np

class Pt:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def tuple(self):
		return (int(self.x),int(self.y))
	
	def __str__(self):
		return f'({self.x},{self.y})'

def interpolate(x, b, e, bp, ep):
	# x: input value
	# b,e: begin and end of input range
	# bp,ep: begin and end of output range
	#return  int((x / (e-b)) * (ep-bp))
	return  (x / (e-b)) * (ep-bp)

def averageTwoPoints(pt1, pt2):
	data = [pt1.tuple(), pt2.tuple()]
	average = [sum(x)/len(x) for x in zip(*data)]
	xc,yc = average

	#x2= pt2.x
	#y2= pt2.y
	#xc = pt1.x + ((x2 - pt1.x) / 2)
	#yc = pt1.y + ((y2 - pt1.y) / 2)
	return Pt(xc,yc)

def triangulateTwoPoints(ptleft, ptright):
	# length of hypotenuse
	lenx = abs(ptright.x - ptleft.x)
	leny = abs(ptright.y - ptleft.y)
	hypotenuse = np.sqrt(lenx**2 + leny**2)

	# point of right angle
	ptr = Pt(ptleft.x, ptright.y)

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
	quadrant = ''
	if ptleft.x < ptright.x and ptleft.y < ptright.y:
		quadrant = 'upper right'
	elif ptleft.x < ptright.x and ptleft.y > ptright.y:
		quadrant = 'upper left'
	elif ptleft.x > ptright.x and ptleft.y < ptright.y:
		quadrant = 'lower right'
	elif ptleft.x > ptright.x and ptleft.y > ptright.y:
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

class Bbox:
	# bbox is defined by an l-t point and a w-h vector, this is what NN data uses
	# redefined with b,r, center, diameter, radius
	def __init__(self, l,t,w,h):
		self.l = l
		self.t = t
		self.w = w
		self.h = h
		self.calc()

	def calc(self):
		# bottom right is a point
		# center is a point
		self.r = self.l + self.w
		self.b = self.t + self.h
		self.center = Pt(self.l+round(self.w/2,6), self.t+round(self.h/2,6))
		self.diameter = (self.w+self.h)/2
		self.radius = self.diameter/2

	def tomm(self,pxlpermm):
		self.l /= pxlpermm
		self.t /= pxlpermm
		self.w /= pxlpermm
		self.h /= pxlpermm
		self.calc()

	def intersects(self, box2):
		if ((self.l > box2.l and self.l < box2.r) or (self.r > box2.l and self.r < box2.r)) \
		and ((self.t > box2.t and self.t < box2.b) or (self.b > box2.t and self.b < box2.b)): 
			return True
		else:
			return False

	# this is a special case of intersects()
	def touchesEdge(self, frameWidth, frameHeight):
		touches = False
		if self.l <= 1 or self.r >= frameWidth-2 \
		or self.t <= 1 or self.b >= frameHeight-2: 
			touches = True
		return touches

	# change name to pad
	def expand(self, padding):
		self.l -= padding
		self.t -= padding
		self.w += (padding*2)
		self.h += (padding*2)
		self.calc()

	# change name to swallow
	def enlarge(self, bbox):
		if self.l > bbox.l:
			self.l = bbox.l
		if self.t < bbox.t:
			self.t = bbox.t
		if self.w < bbox.w:
			self.w = bbox.w
		if self.h < bbox.h:
			self.h = bbox.h
		self.calc()

	def __str__(self):
		prec = 6
		return f'({round(self.l,prec)},{round(self.t,prec)},{round(self.w,prec)},{round(self.h,prec)})'

if __name__ == '__main__':
	a = Pt(1,2)
	a.tuple()

	b = Pt(5,6)
	b.tuple()

	avg = averageTwoPoints(a, b)
	print(a, b, avg)

	degrs, hypotenuse, ptr = triangulateTwoPoints(a, b)
	print(degrs, hypotenuse, ptr)

	qa = quadrantAngle(degrs)
	print(qa)

	qp = quadrantPoints(a,b)
	print(qp)

	c,d = calcLine((20,30), 10, 45)
	print(c,d)

	bb = Bbox(50,60,100,90)
	bb.calc()
	print(bb.r,bb.b,bb.center,bb.diameter,bb.radius)

	ba = Bbox(150,160,200,190)
	intersect = ba.intersects(ba)
	print(intersect)

	bf = Bbox(0,0,640,480)
	touch = ba.touchesEdge(640,480)
	print(touch)

	print(ba)
	ba.expand(5)
	print(ba)

	ba.enlarge(bb)
	print(ba)

	sk8_hsv     = np.array([1,360,360,100,100,100,100,1,1])
	ocv_hsv     = np.array([1,179,179,255,255,255,255,1,1])
	threshholds = np.array([1, 45,135, 50, 75, 10, 25,1,1])
	ocv_set = interpolate(threshholds, 0,sk8_hsv, 0,ocv_hsv)
	print(ocv_set)

