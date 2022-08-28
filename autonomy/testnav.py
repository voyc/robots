''' testnav.py '''

import unittest
import sys
import logging

class TestNav(unittest.TestCase):
	def test_a_vectors(self):
		import numpy as np
		import nav
		logging.info(f'\ndx\tdy\tslope\tangle\tquad\ttheta\t*pi\tdegr\thead\ttheta\tquad\tangle\tslope')
		for test in vectors:
			tvector, tslope, tlength, tangle, ttheta, tquad, thead = test
			dx,dy = tvector
			slope = nav.slopeFromVector(tvector)
			rslope = round(slope,2)
			self.assertEqual( rslope, tslope)

			angle = nav.angleFromSlope(slope)
			rangle = round(angle,3)
			self.assertEqual( rangle, tangle)

			quad = nav.quadFromVector(tvector)
			self.assertEqual( quad, tquad)

			theta = nav.thetaFromAngle(angle,dx,dy)
			rtheta = round(theta,3)
			self.assertEqual( rtheta, ttheta)

			piscalar = round(theta / np.pi,2) # display only
			degr = round(np.degrees(theta),2) # display only

			head = nav.headingFromTheta(theta)
			rhead = round(head,2)
			self.assertEqual( rhead, thead)

			ptheta = nav.thetaFromHeading(head)
			rptheta = round(ptheta,3)
			self.assertEqual( rptheta, ttheta)

			pquad = nav.quadFromTheta(ptheta)
			self.assertEqual( pquad, tquad)

			pangle,_ = nav.angleFromTheta(ptheta)
			rpangle = round(pangle,3)
			self.assertEqual( rpangle, tangle)

			pslope = nav.slopeFromAngle(pangle)
			rpslope = round(pslope,2)
			self.assertEqual( rpslope, tslope)

			logging.info(f'{dx}\t{dy}\t{rslope}\t{rangle}\t{quad}\t{rtheta}\t{piscalar}\t{degr}\t{rhead}\t{rptheta}\t{pquad}\t{rpangle}\t{rpslope}')

	def test_b_headings(self):
		import numpy as np
		import nav
		logging.info(f'\nhead\ttheta\tquad\tangle')
		for test in headings:
			thead, ttheta, tquad, tangle = test

			theta = nav.thetaFromHeading(thead)
			rtheta = round(theta,2)
			self.assertEqual( rtheta, ttheta)

			quad = nav.quadFromTheta(theta)
			angle,_ = nav.angleFromTheta(theta)
			rangle= round(angle,2)
			self.assertEqual( quad, tquad)
			self.assertEqual( rangle, tangle)

			logging.info(f'{thead}\t{rtheta}\t{quad}\t{rangle}')


	def test_c_lines(self):
		import numpy as np
		import nav
		logging.info(f'\ndx\tdy\tslope\tlength\thead')
		for test in vectors:
			tvector, tslope, tlength, tangle, ttheta, tquad, thead = test
			dx,dy = tvector
	
			slope = nav.slopeOfLine([0,0], [dx,dy])
			rslope = round(slope,2)
			self.assertEqual(rslope, tslope)

			length = nav.lengthOfLine([0,0], [dx,dy])
			rlength = round(length,2)
			self.assertEqual(rlength, tlength)

			head = nav.headingOfLine([0,0], [dx,dy])
			rhead = round(head,2)
			#self.assertEqual(rhead, thead)

			logging.info(f'[0,0],\t[{dx},{dy}]\t{rslope}\t{rlength}\t{rhead}')

	def test_d_lines(self):
		import numpy as np
		import nav
		logging.info(f'\nline AB\t\t\tslope\tlength\thead\tperp line LR\t\tslope\thead')
		for test in lines:
			tA, tB, tslope, tlength, thead, tL, tR, tslopeLR, theadLR = test
			r = 50
	
			slope = nav.slopeOfLine(tA,tB)
			rslope = round(slope,2)
			self.assertEqual(rslope, tslope)

			length = nav.lengthOfLine(tA,tB)
			rlength = round(length,2)
			self.assertEqual(rlength, tlength)

			head = nav.headingOfLine(tA,tB)
			rhead = round(head,2)
			self.assertEqual(rhead, thead)

			L,R = nav.linePerpendicular(tA,tB,r)
			rL = (int(L[0]),int(L[1]))
			rR = (int(R[0]),int(R[1]))

			pslope = nav.slopeOfLine(L,R)
			rpslope = round(pslope,2)
			self.assertEqual(rpslope, tslopeLR)

			phead = nav.headingOfLine(L,R)
			rphead = round(phead,2)
			self.assertEqual(rphead, theadLR)

			logging.info(f'{tA},{tB}\t{rslope}\t{rlength}\t{rhead}\t{rL},{rR}\t{rpslope}\t{rphead}')

	def test_e_points(self):
		import numpy as np
		import nav
		logging.info(f'\npoint\t\ttheta\tpoint')
		
		center = [0,0]
		for test in points:
			A, ttheta = test
	
			theta, r = nav.thetaFromPoint(A, center)
			rtheta = round(theta,2)
			self.assertEqual(rtheta, ttheta)

			B = nav.pointFromTheta(center, theta, r)
			rB = (int(B[0]),int(B[1]))
			self.assertEqual(rB, A)

			logging.info(f'{A}\t{rtheta}\t{rB}')
	
	def test_f_drawperps(self):
		import numpy as np
		import nav
		import matplotlib.pyplot as plt  
		import matplotlib
		import math
		import hippoc
		from PIL import Image
		from PIL import ImageChops
		from PIL import ImageStat

		name = 'drawperps'
		testname = f'xtemp_{name}.png'
		refname = f'ref_{name}.png'
		r = 70

		for test in drawperps:
			A, B = test
			nav.drawLine([A,B])

			L,R = nav.linePerpendicular(A, B, r)
			thetaL,_ = nav.thetaFromPoint(L, B)
			thetaR,_ = nav.thetaFromPoint(R, B)
			E = nav.pointFromTheta(B, thetaL, r)
			F = nav.pointFromTheta(B, thetaR, r)

			nav.drawPoint(E, size=100, color='cyan')
			nav.drawPoint(F, size=100, color='pink')
			nav.drawPoint(A, color='yellow')
			nav.drawPoint(B, color='green')
			nav.drawPoint(L, color='blue')
			nav.drawPoint(R, color='red')

			a = matplotlib.patches.Arc(B, r*2, r*2, 0, math.degrees(thetaR), math.degrees(thetaL), color='chartreuse')
			plt.gca().add_patch(a)
			a = matplotlib.patches.Arc(B, r*2, r*2, 0, math.degrees(thetaL), math.degrees(thetaR), color='orange')
			plt.gca().add_patch(a)

		plt.xlim(0,1000)
		plt.ylim(0,1000)
		plt.autoscale(False)
		plt.gca().set_aspect('equal', anchor='C')

		plt.savefig(testname)

		im1 = Image.open(testname)
		im2 = Image.open(refname)
		diff = ImageChops.difference(im1, im2)
		stat = ImageStat.Stat(diff)
		ratio = (sum(stat.mean) / (len(stat.mean) * 255)) * 100 
		self.assertEqual(ratio, 0)

		if not runquiet:
			plt.show()


	def test_g_drawarena(self):
		import numpy as np
		import nav
		import matplotlib.pyplot as plt  
		import matplotlib
		import math
		import hippoc
		from PIL import Image
		from PIL import ImageChops
		from PIL import ImageStat

		name = 'drawarena'
		testname = f'xtemp_{name}.png'
		refname = f'ref_{name}.png'

		plt.gcf().clear()

		cones = nav.conesfreestyle
		
		cones = hippoc.calcCones(cones, hippoc.skate_spec)
		route = hippoc.plotRoute(cones, hippoc.skate_spec)
		hippoc.drawArena(cones, hippoc.arena_spec, test=True)
		hippoc.drawRoute(route, hippoc.arena_spec, hippoc.skate_spec)

		plt.savefig(testname)

		im1 = Image.open(testname)
		im2 = Image.open(refname)
		diff = ImageChops.difference(im1, im2)
		stat = ImageStat.Stat(diff)
		ratio = (sum(stat.mean) / (len(stat.mean) * 255)) * 100 
		self.assertEqual(ratio, 0)

		if not runquiet:
			plt.show()

	def test_h_arcs(self):
		import numpy as np
		import nav
		import matplotlib.pyplot as plt
		import math
		from PIL import Image
		from PIL import ImageChops
		from PIL import ImageStat

		name = 'drawarcs'
		testname = f'xtemp_{name}.png'
		refname = f'ref_{name}.png'

		plt.gcf().clear()

		r = 50
		center = [0,0]
		nav.drawCircle(center, r) 

		def testone(n, test):
			nonlocal r, center
			tt1, tt2, trdir, tlen = test
			r += 50 
			
			pi1 = round(tt1/np.pi,2)
			pi2 = round(tt2/np.pi,2)

			len  = nav.lengthOfArc(tt1, tt2, r, trdir)
			lend = math.degrees(nav.lengthOfArcTheta(tt1, tt2, r, trdir))
			rlen  = int(len)
			rlend = round(lend,1)
			self.assertEqual(rlen, tlen)

			p1 = nav.pointFromTheta(center, tt1, r)
			nav.drawPoint(p1,color='green')
			p2 = nav.pointFromTheta(center, tt2, r)
			nav.drawPoint(p2,color='red')

			color = 'red' if trdir == 'ccw' else 'green'
			nav.drawArc(tt1, tt2, trdir, center, r, color=color)

			logging.info(f'{n}\t{tt1}\t{tt2}\t{pi1}\t{pi2}\t{trdir}\t{rlend}\t{rlen}')

		logging.info(f'\nn\tt1\tt2\tpi\tpi\trdir\tlend\tlen')
		

		plt.xlim(-1050, 1050)
		plt.ylim(-1050, 1050)
		plt.autoscale(False)
		plt.gca().set_aspect('equal', anchor='C')

		for t in [1,2,7,8]:
			testone(t, arcs[t-1])

		r += 100 
		for t in [5,6,19,20]:
			testone(t, arcs[t-1])

		r += 100 
		for t in [41,42]:
			testone(t, arcs[t-1])

		plt.savefig(testname)

		im1 = Image.open(testname)
		im2 = Image.open(refname)
		diff = ImageChops.difference(im1, im2)
		stat = ImageStat.Stat(diff)
		ratio = (sum(stat.mean) / (len(stat.mean) * 255)) * 100 
		self.assertEqual(ratio, 0)

		if not runquiet:
			plt.show()

# ---------------- test data ------------------#
	
inf = float('inf') # copied from nav.py

vectors = [
	#  vector, slope,  len,  angle,  theta, q,   head
	[[+4,  0],  0.0 , 4.0 ,  0.0  ,  0.0  , 1,  90.0 ],  # I
	[[+4, +1],  0.25, 4.12,  0.245,  0.245, 1,  75.96],
	[[+4, +2],  0.5 , 4.47,  0.464,  0.464, 1,  63.43],
	[[+4, +3],  0.75, 5.0 ,  0.644,  0.644, 1,  53.13],
	[[+4, +4],  1.0 , 5.66,  0.785,  0.785, 1,  45.0 ],
	[[+3, +4],  1.33, 5.0 ,  0.927,  0.927, 1,  36.87],
	[[+2, +4],  2.0 , 4.47,  1.107,  1.107, 1,  26.57],
	[[+1, +4],  4.0 , 4.12,  1.326,  1.326, 1,  14.04],
	[[ 0, +4], -inf , 4.0 , -1.571,  1.571, 2,   0.0 ],  # II
	[[-1, +4], -4.0 , 4.12, -1.326,  1.816, 2, 345.96],
	[[-2, +4], -2.0 , 4.47, -1.107,  2.034, 2, 333.43],
	[[-3, +4], -1.33, 5.0 , -0.927,  2.214, 2, 323.13],
	[[-4, +4], -1.0 , 5.66, -0.785,  2.356, 2, 315.0 ],
	[[-4, +3], -0.75, 5.0 , -0.644,  2.498, 2, 306.87],
	[[-4, +2], -0.5 , 4.47, -0.464,  2.678, 2, 296.57],
	[[-4, +1], -0.25, 4.12, -0.245,  2.897, 2, 284.04],
	[[-4,  0], -0.0 , 4.0 , -0.0  ,  3.142, 3, 270.0 ],  # III
	[[-4, -1],  0.25, 4.12,  0.245,  3.387, 3, 255.96],
	[[-4, -2],  0.5 , 4.47,  0.464,  3.605, 3, 243.43],
	[[-4, -3],  0.75, 5.0 ,  0.644,  3.785, 3, 233.13],
	[[-4, -4],  1.0 , 5.66,  0.785,  3.927, 3, 225.0 ],
	[[-3, -4],  1.33, 5.0 ,  0.927,  4.069, 3, 216.87],
	[[-2, -4],  2.0 , 4.47,  1.107,  4.249, 3, 206.57],
	[[-1, -4],  4.0 , 4.12,  1.326,  4.467, 3, 194.04],
	[[ 0, -4], -inf , 4.0 , -1.571,  4.712, 4, 180.0 ],  # IV
	[[+1, -4], -4.0 , 4.12, -1.326,  4.957, 4, 165.96],
	[[+2, -4], -2.0 , 4.47, -1.107,  5.176, 4, 153.43],
	[[+3, -4], -1.33, 5.0 , -0.927,  5.356, 4, 143.13],
	[[+4, -4], -1.0 , 5.66, -0.785,  5.498, 4, 135.0 ],
	[[+4, -3], -0.75, 5.0 , -0.644,  5.64 , 4, 126.87],
	[[+4, -2], -0.5 , 4.47, -0.464,  5.82 , 4, 116.57],
	[[+4, -1], -0.25, 4.12, -0.245,  6.038, 4, 104.04],
]

headings = [
	# head,theta, q, angle
	[  0.0, 1.57, 2, -1.57],
	[ 22.5, 1.18, 1,  1.18],
	[ 45.0, 0.79, 1,  0.79],
	[ 67.5, 0.39, 1,  0.39],
	[ 90.0, 0.0 , 1,  0.0 ],
	[112.5, 5.89, 4, -0.39],
	[135.0, 5.5 , 4, -0.79],
	[157.5, 5.11, 4, -1.18],
	[180.0, 4.71, 4, -1.57],
	[202.5, 4.32, 3,  1.18],
	[235.0, 3.75, 3,  0.61],
	[257.5, 3.36, 3,  0.22],
	[270.0, 3.14, 3,  0.0 ],
	[291.5, 2.77, 2, -0.38],
	[315.0, 2.36, 2, -0.79],
	[337.5, 1.96, 2, -1.18],
	[360.0, 1.57, 2, -1.57],
]

lines = [#   A         B         slope  length    head     L          R        slope    head
	[[100, 100], [900, 900],  1.0 , 1131.37, 45.0  , (864, 935),(935, 864), -1.0 , 135.0 ],  # ur
	[[800, 300], [200, 600], -0.5 ,  670.82, 296.57, (177, 555),(222, 644),  2.0 , 26.57 ],  # ul
	[[900, 600], [100, 300],  0.38,  854.4 , 249.44, (117, 253),(82, 346),  -2.67, 339.44],  # ll
	[[100, 900], [900, 100], -1.0 , 1131.37, 135.0 , (935, 135),(864, 64),   1.0 , 225.0 ],  # lr
]

arcs = [
	[0.927, 2.356, 'ccw',  142,],  #  1 * from q1 to qr2
	[0.927, 2.356, 'cw' ,  728,],  #  2 * ditto
	[0.927, 3.927, 'ccw',    0,],  #  3
	[0.927, 3.927, 'cw' ,    0,],  #  4
	[0.927, 5.498, 'ccw', 1828,],  #  5 ** from q1 to q4
	[0.927, 5.498, 'cw' ,  770,],  #  6 ** ditto
	[2.356, 0.927, 'ccw',  970,],  #  7 * from q2 to q1
	[2.356, 0.927, 'cw' ,  357,],  #  8 * ditto
	[2.356, 3.927, 'ccw',    0,],  #  9
	[2.356, 3.927, 'cw' ,    0,],  # 10
	[2.356, 5.498, 'ccw',    0,],  # 11
	[2.356, 5.498, 'cw' ,    0,],  # 12
	[3.927, 0.927, 'ccw',    0,],  # 13
	[3.927, 0.927, 'cw' ,    0,],  # 14
	[3.927, 2.356, 'ccw',    0,],  # 15
	[3.927, 2.356, 'cw' ,    0,],  # 16
	[3.927, 5.498, 'ccw',    0,],  # 17
	[3.927, 5.498, 'cw' ,    0,],  # 18 
	[5.498, 0.927, 'ccw',  856,],  # 19 ** from q4 to q1
	[5.498, 0.927, 'cw' , 2514,],  # 20 ** ditto
	[5.498, 2.356, 'ccw',    0,],  # 21
	[5.498, 2.356, 'cw' ,    0,],  # 22
	[5.498, 3.927, 'ccw',    0,],  # 23
	[5.498, 3.927, 'cw' ,    0,],  # 24
	[5.498, 0.000, 'ccw',    0,],  # 25
	[5.498, 0.000, 'cw' ,    0,],  # 26
	[2.356, 1.571, 'ccw',    0,],  # 27
	[2.356, 1.571, 'cw' ,    0,],  # 28
	[3.927, 3.142, 'ccw',    0,],  # 29
	[3.927, 3.142, 'cw' ,    0,],  # 30
	[0.927, 4.712, 'ccw',    0,],  # 31
	[0.927, 4.712, 'cw' ,    0,],  # 32
	[0.000, 5.498, 'ccw',    0,],  # 33
	[0.000, 5.498, 'cw' ,    0,],  # 34
	[1.571, 2.356, 'ccw',    0,],  # 35
	[1.571, 2.356, 'cw' ,    0,],  # 36
	[3.142, 3.927, 'ccw',    0,],  # 37
	[3.142, 3.927, 'cw' ,    0,],  # 38
	[4.712, 0.927, 'ccw',    0,],  # 39
	[4.712, 0.927, 'cw' ,    0,],  # 40
	[5.498, 5.498, 'ccw',    0,],  # 41 *** from and to are same point, ccw go nowhere
	[5.498, 5.498, 'cw' , 4712,],  # 42 ***                             cw go all the way around
]

points = [#  pt      
	[(100, 100), 0.79, ],
	[(800, 300), 0.36, ],
	[(900, 600), 0.59, ],
	[(100, 900), 1.46, ],
	[(900, 900), 0.79, ],
	[(200, 600), 1.25, ],
	[(100, 300), 1.25, ],
	[(900, 100), 0.11, ],
]


drawperps = [ # A           B     
	[(100, 100), (900, 900), ],
	[(800, 300), (200, 600), ],
	[(900, 600), (100, 300), ],
	[(100, 900), (900, 100), ],
]

if __name__ == '__main__':
	global runquiet
	runquiet = True
	logging.basicConfig(format='%(message)s')
	if not set(['--quiet', '-q']) & set(sys.argv):
		runquiet = False
		logging.getLogger('').setLevel(logging.INFO)

	unittest.main(argv=['ignored'], exit=False) # run methods named "test_..." in alphabetical order

