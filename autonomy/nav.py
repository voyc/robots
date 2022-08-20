''' nav.py


Terms

	Heading - direction the vehicle is pointing
	Course - direction the vehicle is moving, may be different from heading due to drift
	Bearing - direction to destination or navigational aid
	Relative bearing - angle between heading and bearing

	angle - the angle within the right triangle, always < 90 degrees (in radians)
	theta - the obtuse angle indicating direction within the circle (in radians)

units conventions:
	radians - 2pi to a circle, oriented at 3 o'clock
	compass degrees - 360 to a circle, oriented to 12 o'clock

	heading, course and bearing are given in compass degrees
	relative bearing is given in degrees
	angle and theta are given in radians

trigonometry functions, soh cah toa
	sine
	cosine
	tangent

an inverse function undoes the function
	arctangent is the inverse of tangent

ratio = tan(angle)	# tangent takes an angle and returns a ratio 
angle = arctan(ratio)	# arctangent takes the ratio and returns the angle
slope = tan(theta)	# toa, ratio of opposite to adjacent, y/x, slope      
theta = arctan(slope)	# inverse of tangent, get the angle theta from the slope  

slope does not distinguish between lines going up or down
positive slope indicates a direct relationship between x and y
negative slope indicates an inverse relationship between x and y
negative change in y means line is going down, else up 
negative change in x means line is going left, else right

theta does distinguish between lines going up or down
theta is an obtuse angle between 0 and 2pi
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

an angle can be expressed as radians or degrees
let angle refer to the angle within a right triangle, always < 90 degrees or pi/2
let theta refer to the obtuse angle relative to the right-side x axis

slope = ratio dy/dx = tan(angle)   # tan() returns a ratio
angle = arctan(dy/dx)              # arctan() returns an angle in radians

-90 degrees < angle < +90 degrees 
 -1.57 rads < angle < +1.57 rads      # pi/2 = 1.57

if dy/dx is negative, arctan(dy/dx) is negative (in quadrants 2 and 4)


sides -> ratio -> angle -> theta -> heading
dx,dy -> dy/dx -> arctan() -> theta -> heading
sides = dx,dy
ratio = dy/dx
angle = arctan(ratio)
theta = thetaFromAngle(angle,dx,dy)
heading = headingFromTheta(theta)
where
     angle is between +-pi/2 radians, oriented to right triangle
     theta is between +=2pi radians, oriented to horizontal axis pointing right
     heading is between 0-360 degrees, oriented to straight up north

  ----slope----    angle   -----theta----- heading   quadrant
                           rads   *pi degr 
  inf +dy / 0dx     1.57   1.57  0.50   90       0   vertical north 
    1 +dy / +dx     0.79   0.79  0.25   45      45   ur quadrant 1 
    0 0dy / +dx        0   0     0       0      90   horizontal east 
   -1 +dy / -dx    -0.79   5.50  1.75  315     135   lr quadrant 4 
  inf -dy / 0dx    -1.57   4.71  1.50  270     180   vertical south     
    1 -dy / -dx     0.79   3.93  1.25  225     225   ll quadrant 3
    0 0dy / -dx        0   3.14  1.00  180     270   horizontal west
   -1 +dy / -dx    -0.79   2.35  0.75  135     315   ul quadrant 2

'''
import numpy as np
import matplotlib.pyplot as plt  
import matplotlib
import math

def reckon(startpos, heading, distance):
	# dead reckoning, return endpos

	# soh cah toa
	# dy is opposite
	# dx is adjacent
	# distance is hypotenuse
	# theta and angle can be derived from heading

	theta = thetaFromHeading(heading)
	angle = angleFromTheta(theta)
	dy = np.sin(angle) * distance # soh : sin(a) = oppo/hypo : sin(angle) = dy/distance
	dx = np.cos(angle) * distance # cah : cos(a) = adj/hypo  : sin(angle) = dx/distance
	endpos = startpos + np.array([dx,dy])
	return endpos

def calcLineWithHeading(center, heading, length):
	half = length / 2
	theta = thetaFromHeading(heading)
	dy = np.sin(theta) * half
	dx = np.cos(theta) * half
	A = center + np.array([dx,dy])
	B = center - np.array([dx,dy])
	return [A,B]

'''
angle vs theta
	both are given in radians

	angle can indicate one of four thetas, depending on quadrant
	dx,dy are required to determine quadrant

	conversion function:
		theta = thetaFromAngle(angle, dx, dy)
		angle = angleFromTheta(theta)
'''

def thetaFromAngle(angle, dx, dy): 
	# combine arctan to make obtuse angle depending on quadrant
	if dx > 0 and dy < 0:  # quadrant 4
		theta = (2 * np.pi) + angle
	elif dx < 0:  # quadrant 2 & 3
		theta = angle + np.pi
	else:  # quadrant 1
		theta = angle 
	return theta

def angleFromTheta(theta): 
	for i in range(4):
		angle = theta - (i * 0.5 * np.pi) 
		if angle > 0: break;
	return angle

'''
heading vs theta
	heading and theta both indicate direction within a circle

	heading is given in compass degrees, 0 to 360, clockwise
	theta is given in radians, 0 to 2pi, counter-clockwise
	
	theta is used in the matplotlib Arc() function
	heading is used by humans

	conversion functions:
		theta = thetaFromHeading(heading)
		heading = headingFromTheta(theta)
'''

def headingFromTheta(theta):
	degr = math.degrees(theta)
	degr = 90 - degr
	if degr < 0:
		degr = 360 + degr
	heading = degr
	return heading 

def thetaFromHeading(heading):
	degr = 360 + 90 - heading
	if degr > 360:
		degr -= 360
	theta = math.radians(degr)
	return theta

# rename to slopeFromLine
def lineSlope(A,B):
	dy = (B[1] - A[1])
	dx = (B[0] - A[0])
	if dx == 0: dx = .0001
	slope = dy / dx
	return slope, dy, dx

# rename to headingFromLine
def lineHeading(A,B):  # calc compass heading of a line
	slope, dy, dx = lineSlope(A,B)
	atan = np.arctan(slope)
	theta = thetaFromAngle(atan, dx, dy)
	degrees = math.degrees(theta)
	heading = headingFromTheta(theta)
	return heading

# rename to cartFromPolar, and change order of arguments
def polar2cart(r, theta, center):
	x = r * np.cos(theta) + center[0]
	y = r * np.sin(theta) + center[1]
	return x, y

# linePerpendicularToLine
def calcPerpendicular(A,B,r):
		# calculate a line segment LR 
		#     perpendicular to AB
		#     with length 2r
		#     intersecting B
		#     with L on the left, and R on the right
		# see https://stackoverflow.com/questions/57065080/draw-perpendicular-line-of-fixed-length-at-a-point-of-another-line
		# return two points, in both cartesian and polar coordinates

		# calc slope of AB
		slopeAB = (B[1] - A[1]) / (B[0] - A[0])
		left2right = (B[0] - A[0]) > 0
		lo2hi = (B[1] - A[1]) > 0

		# slope of LR as dy/dx
		dy = math.sqrt(r**2/(slopeAB**2+1))
		dx = -slopeAB*dy
		diff = np.array([dx, dy])

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

		return L, R, thetaL, thetaR

if __name__ == '__main__':
	def test(A,B,r):
		x,y = np.transpose([A,B])
		plt.plot(x,y, color='black', lw=1)
		L, R, thetaL, thetaR = calcPerpendicular(A, B, r)
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

		slope, dy, dx = lineSlope(A,B)
		heading = lineHeading(A,B)
		atan = np.arctan(slope)
		theta = thetaFromAngle(atan, dx, dy)
		degrees = math.degrees(theta)
		heading = headingFromTheta(theta)
		theta2 = thetaFromHeading(heading)
		print(f'{A}\t{B}\t{slope}\t{round(atan,2)}\t{round(theta,2)}\t{round(degrees)}\t{round(heading)}\t{theta2}')

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
