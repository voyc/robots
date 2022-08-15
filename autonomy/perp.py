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


def radian2compass(radians): return math.degrees(radians) - 90
def compass2radians(compass): return math.radians(compass + 90)

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

	r = 50
	
	A = np.array([100, 100]); B = np.array([900, 900])  # ur
	test(A,B,r)
	
	A = np.array([900, 600]); B = np.array([100, 300])  # ll
	test(A,B,r)
	
	A = np.array([100, 900]); B = np.array([900, 100])  # lr
	test(A,B,r)
	
	A = np.array([900, 300]); B = np.array([100, 600])  # ul
	test(A,B,r)
	
	# draw arena
	plt.xlim(0,1000)
	plt.ylim(0,1000)
	plt.autoscale(False)
	plt.gca().set_aspect('equal', anchor='C')
	plt.show()
