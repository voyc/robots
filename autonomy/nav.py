''' nav.py

trigonometry for navigation

for documentation:
    see https://github.com/voyc/robots/wiki/Navigation-Trigonometry
    run the unit test program: testnav.py
'''

import numpy as np
import math
import matplotlib
import matplotlib.pyplot as plt

inf = float('inf')   # note: -inf == float('-inf')

def slopeFromVector(vector):
	dx,dy = vector
	if dx == 0:
		slope = -inf # if dy < 0 else inf
	else:
		slope = dy/dx
	return slope

def quadFromVector(vector): 
	dx,dy = vector
	quad = 0
	if   dx >  0 and dy >= 0: quad = 1
	elif dx <= 0 and dy >  0: quad = 2
	elif dx <  0 and dy <= 0: quad = 3
	elif dx >= 0 and dy <  0: quad = 4
	return quad

def quadFromTheta(theta): 
	quad = 0
	piscalar =  theta/np.pi 
	if   piscalar < 0.5: quad = 1
	elif piscalar < 1.0: quad = 2
	elif piscalar < 1.5: quad = 3
	elif piscalar < 2.0: quad = 4
#	else: 
#		print('piscalar is ', piscalar)
#		quad = 4
#	
	return quad

def angleFromSlope(slope):
	return np.arctan(slope)

def slopeFromAngle(angle):
	slope = np.tan(angle)
	if slope < -1e+15: slope = -inf
	return slope

def thetaFromAngle(angle, dx, dy): 
	q = quadFromVector([dx,dy])
	if q == 1: theta = angle
	if q == 2: theta = angle + np.pi
	if q == 3: theta = angle + np.pi
	if q == 4: theta = (2 * np.pi) + angle   
	if theta > (2*np.pi):
		print('thetaFromAngle',angle,dx,dy,theta,q)
		quit()
	return theta

def headingFromTheta(theta):
	degr = math.degrees(theta)
	degr = 90 - degr
	if degr < 0:
		degr = 360 + degr
	heading = degr
	return heading 

def thetaFromHeading(heading):
	degr = 360 + 90 - heading
	if degr >= 360:
		degr -= 360
	theta = math.radians(degr)
	return theta

def angleFromTheta(theta): 
	q = quadFromTheta(theta)
	if q == 1: angle = theta
	if q == 2: angle = theta - np.pi
	if q == 3: angle = theta - np.pi
	if q == 4: angle = theta - (2*np.pi)
	return angle,q

def vectorOfLine(A,B):
	dy = (B[1] - A[1])
	dx = (B[0] - A[0])
	return dx,dy

def slopeOfLine(A,B):
	dx,dy = vectorOfLine(A,B)
	slope = slopeFromVector([dx,dy])
	return slope

def lengthOfLine(A,B):
	dx,dy = vectorOfLine(A,B)
	hyp = math.sqrt((dx*dx) + (dy*dy)) # pythagorean theorem
	return hyp

def headingOfLine(A,B):  # calc compass heading of a line
	dx,dy = vectorOfLine(A,B)
	slope = slopeFromVector([dx,dy])
	angle = angleFromSlope(slope)
	theta = thetaFromAngle(angle, dx, dy)
	heading = headingFromTheta(theta)
	return heading

def thetaFromPoint(pt,center):
	dx,dy = vectorOfLine(center, pt)
	length = lengthOfLine(center, pt)
	slope = slopeFromVector([dx,dy])
	angle = angleFromSlope(slope)
	theta = thetaFromAngle(angle, dx, dy)
	return theta, length

def pointFromTheta(center, theta, r):
	dx,dy = vectorFromTheta( theta, r)
	return center + np.array([dx,dy])

def vectorFromTheta( theta, r):
	a,q = angleFromTheta(theta)
	dx = r * abs(np.cos(a))
	dy = r * abs(np.sin(a))
	if q in (2,3): 
		dx *= -1
	if q in (3,4):
		dy *= -1
	return dx,dy

def lineFromHeading(center, heading, length):
	half = length / 2
	theta = thetaFromHeading(heading)
	dx,dy = vectorFromTheta( theta, half)
	A = center + np.array([dx,dy])
	B = center - np.array([dx,dy])
	return [A,B]

def linePerpendicular(A,B,r):
	# calculate a line segment LR perpendicular to AB
	# see https://stackoverflow.com/questions/57065080/draw-perpendicular-line-of-fixed-length-at-a-point-of-another-line
	headAB = headingOfLine(A,B)
	headLR = headAB - 90
	if headLR < 0:
		headLR += 360
	L,R = lineFromHeading(B, headLR, 2*r)
	return L,R

#---------- functions above this line are in unit test ----------------#

def isPointPastLine(A,B,C):
	# is pt C past the line from A to B, yes or no
	ab = lengthOfLine(A,B)
	ac = lengthOfLine(A,C)
	return (ac > ab)


def reckonLine(startpos, heading, distance):
	# dead reckoning, return new position along a line
	theta = thetaFromHeading(heading)
	dx,dy = vectorFromTheta(theta, distance)
	endpos = startpos + np.array([dx,dy])
	return endpos

def lengthOfArc(tfrom, tto, r, rdir):
	tcircle = 2*np.pi
	lencircle = 2 * np.pi * r  # circumference
	tarc = lengthOfArcTheta(tfrom, tto, r, rdir)
	lenarc =  (tarc/tcircle) * lencircle  # tarc/tcircle = lenarc/lencircle
	return lenarc

def lengthOfArcTheta(tfrom, tto, r, rdir):
	if rdir == 'ccw':
		tdiff = tto - tfrom
		if tdiff < 0:
			tdiff += 2*np.pi
	elif rdir == 'cw':
		tdiff = tfrom - tto
		if tdiff <= 0:  # if to and from are same point, cw goes all the way around
			tdiff += 2*np.pi
	else:
		tdiff = 42
	return tdiff

def reckonArc(theta1, distance, r, wise):  # no center?
	# find next theta given distance, distance == arc length
	# ratio: distance / circumference = theta / 2pi
	# distance / (2*np.pi*r) =  theta / (2*np.pi)
	# (distance * 2*np.pi)/(np.pi*2*r) =  (theta / (2*np.pi))
	rot = -1 if wise == 'cw' else 1 # rotational direction
	thetadiff =  distance/r
	thetadiff *= rot
	theta2 =  theta1 + thetadiff
	if (theta2/np.pi) > 2:
		theta2 -= (2*np.pi)
		#print(theta1, thetadiff, theta2)
		#quit()
	return theta2

def isThetaPastArc(a, b, c, center, r, rdir):
	ab = lengthOfArcTheta(a, b, r, rdir)
	ac = lengthOfArcTheta(a, c, r, rdir)
	return ac > ab

# --------------- drawing --------------- #

def drawPoint(pt, color='black', size=36): 
	x,y = pt #np.transpose(pt); 
	plt.scatter(x,y,c=color, s=size)

def drawLine(line, color='black'): 
	x,y = np.transpose(line); 
	plt.plot(x,y, color=color, lw=1)

def drawCircle( center, r, color='black'):
	c = plt.Circle(center, r, fill=False); 
	plt.gca().add_patch(c)

def drawArc(tfrom, tto, rdir, center, r, color='black'): 
	t1 = tfrom
	t2 = tto
	if rdir == 'cw': 
		t1 = tto
		t2 = tfrom
		if t1 == t2:
			t2 -= .001
	a = matplotlib.patches.Arc(center, r*2, r*2, 0, math.degrees(t1), math.degrees(t2), color=color)
	plt.gca().add_patch(a)

# --------------- test data ------------- #

conesfreestyle = [
	{'center':[1704.5,  667. ], 'rdir':'ccw' }, 
	{'center':[3588.5, 1410. ], 'rdir':'ccw' }, # +slope, +dy, +dx, up  , to the right, quadrant 1
	{'center':[1294.5, 3333. ], 'rdir':'ccw' }, # -slope, +dy, -dx, up  , to the left , quadrant 2
	{'center':[2928.5, 2561. ], 'rdir':'ccw' }, # -slope, -dy, +dx, down, to the right, quadrant 4
	{'center':[ 411.5,  787. ], 'rdir':'ccw' }, # +slope, -dy, -dx, down, to the left , quadrant 3
]

if __name__ == '__main__':
	pass
