''' nav.py

directions in compass degrees:
	Heading - direction the aircraft is pointing

	Course - direction the aircraft is moving, may be different from heading due to drift

	Bearing - direction to destination or nav aid

	Relative bearing - angle between heading and bearing

compass degrees - 360 to a circle, oriented to 12 o'clock
radians - 2pi to a circle, oriented at 3 o'clock
'''

import numpy as np
import matplotlib.pyplot as plt  
import matplotlib
import math

'''
a reciprocal function does... what?
cotangent is the reciprocal of tangent

an inverse function undoes the function
arctangent is the inverse of tangent

ratio = tan(angle)	# tangent takes an angle and returns a ratio 
angle = arctan(ratio)	# arctangent takes the ratio and returns the angle
slope = tan(theta)	# toa, ratio of opposite to adjacent is y/x, ie slope      
theta = arctan(slope)	# inverse of tangent, get the angle from the slope  

	# slope(A) = tan(A)
	# A = arctan(slope(A))

slope does not distinguish between lines going up or down
positive slope indicates a direct relationship between x and y
negative slope indicates an inverse relationship between x and y
negative change in y means line is going down, else up 
negative change in x means line is going left, else right

theta does distinguish between lines going up or down
theta between 0 and pi indicates the line is going up
theta between pi and 2pi indicates the line is going down

-dy, -dx => +slope, down to the left , quadrant 3 ll
+dy, +dx => +slope, up   to the right, quadrant 1 ur
-dy, +dx => -slope, down to the right, quadrant 4 lr
+dy, -dx => -slope, up   to the left , quadrant 2 ul

theta should always be positive
arctan(negative slope) returns a negative theta

as slope approaches vertical from the right it approaches infinity
as slope approaches vertical from the left it approaches -infinity

  ----slope----    arctan  -----theta----- heading   quadrant
                           rads   *pi degr 
  inf +dy / 0dx     1.57   1.57  0.50   90       0   vertical north 
    1 +dy / +dx     0.79   0.79  0.25   45      45   ur 
    0 0dy / +dx        0   0     0       0      90   horizontal east 
   -1 +dy / -dx    -0.79   5.50  1.75  315     135   lr 
  inf -dy / 0dx    -1.57   4.71  1.50  270     180   vertical south     
    1 -dy / -dx     0.79   3.93  1.25  225     225   ll 
    0 0dy / -dx        0   3.14  1.00  180     270   horizontal west
   -1 +dy / -dx    -0.79   2.35  0.75  135     315   ul 

'''
def t2h(theta):
	h = 360 - theta + 90
	if h >= 360:
		h -= 360
	return h

def r2p(rad):
	p = rad / np.pi
	return p

def atan2theta(atan, dx, dy):
	if dx > 0 and dy < 0:  #q4
		theta = (2 * np.pi) + atan
	elif dx < 0:  # q2 & q3
		theta = atan + np.pi
	else:   # q1
		theta = atan 
	return theta

def calcHeading(A,B):
	dy = (B[1] - A[1])
	dx = (B[0] - A[0])
	if dx == 0: dx = .0001
	slope = dy / dx
	atan = np.arctan(slope)
	theta = atan2theta(atan, dx, dy)
	degrees = math.degrees(theta)
	heading = radian2compass(theta)
	theta2 = compass2radians(heading)
	print(f'{A}\t{B}\t{slope}\t{round(atan,2)}\t{round(theta,2)}\t{round(degrees)}\t{round(heading)}\t{theta2}')
	return heading


def radian2compass(radians): 
	degr = math.degrees(radians)
	degr = 90 - degr
	if degr < 0:
		degr = 360 + degr
	return degr

def compass2radians(degr): 
	degr = 360 + 90 - degr
	if degr > 360:
		degr -= 360
	rads = math.radians(degr)
	return rads

def polar2cart(r, theta, center):
	x = r * np.cos(theta) + center[0]
	y = r * np.sin(theta) + center[1]
	return x, y

def calcPerpendicular(A,B,r):
		# calculate a line segment LR 
		#     perpendicular to AB
		#     with length 2r
		#     intersecting B
		#     with L on the left, and R on the right
		# see https://stackoverflow.com/questions/57065080/draw-perpendicular-line-of-fixed-length-at-a-point-of-another-line

		# calc slope of AB
		slopeAB = (B[1] - A[1]) / (B[0] - A[0])
		left2right = (B[0] - A[0]) > 0
		lo2hi = (B[1] - A[1]) > 0

		# slope of LR as dy/dx
		dy = math.sqrt(r**2/(slopeAB**2+1))
		dx = -slopeAB*dy
		diff = [dx, dy]

		# calc endpoints L and R

		if left2right:
			L = B + diff
			R = B - diff
		else:
			L = B - diff
			R = B + diff

		# calc theta for L and R
		if lo2hi:
			thetaR = np.arctan(dy/dx)
			thetaL = thetaR + math.pi
		else:
			thetaL = np.arctan(dy/dx)
			thetaR = thetaL + math.pi 

		return L, R, thetaL, thetaR, left2right, lo2hi

if __name__ == '__main__':
	def test(A,B,r):
		x,y = np.transpose([A,B])
		plt.plot(x,y, color='black', lw=1)
		L, R, thetaL, thetaR,_,_ = calcPerpendicular(A, B, r)
		E = polar2cart(r, thetaL, B)
		F = polar2cart(r, thetaR, B)
		plt.scatter(E[0], E[1], s=100, c='cyan')
		plt.scatter(F[0], F[1], s=100, c='pink')
		plt.scatter(A[0], A[1], c='yellow')
		plt.scatter(B[0], B[1], c='green')
		plt.scatter(L[0], L[1], c='blue')
		plt.scatter(R[0], R[1], c='red')
		a = matplotlib.patches.Arc(B, r*2, r*2, 0, math.degrees(thetaR), math.degrees(thetaL), color='chartreuse')
		plt.gca().add_patch(a)
		a = matplotlib.patches.Arc(B, r*2, r*2, 0, math.degrees(thetaL), math.degrees(thetaR), color='orange')
		plt.gca().add_patch(a)
		calcHeading(A,B)

	r = 50
	
	print('A\t\tB\t\tslope\tatan\ttheta\tdegrees\theading')

	A = np.array([100, 100]); B = np.array([900, 900])  # ur
	test(A,B,r)
	
	A = np.array([900, 300]); B = np.array([100, 600])  # ul
	test(A,B,r)
	
	A = np.array([900, 600]); B = np.array([100, 300])  # ll
	test(A,B,r)
	
	A = np.array([100, 900]); B = np.array([900, 100])  # lr
	test(A,B,r)
	
	# draw arena
	plt.xlim(0,1000)
	plt.ylim(0,1000)
	plt.autoscale(False)
	plt.gca().set_aspect('equal', anchor='C')
	plt.show()
