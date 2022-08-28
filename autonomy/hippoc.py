''' hippoc.py '''

import numpy as np
import matplotlib.pyplot as plt  
import matplotlib  
import mpmath  
import math
import nav
from matplotlib.animation import FuncAnimation 
import copy
import sys
import logging

# all measurements are in cm's, and 1 cm == 1 pixel
# speed is in kph, and internally changed to cps
# x,y pixel positions in the arena stand in for lng,lat coordinates

arena_spec = {
	'w':4000,
	'h': 4000,
	'title': 'Arena',
	'gate': [2000,50],
	'conecolor': 'cyan',
	'routecolor': 'black'
}

event_spec = {
	'event': 'freestyle',
	'num_cones': 5,
}

skate_spec = {
	'turning_radius': 200,
	'length': 70,
	'width':  20,
	'avgspeed': 15, # kmh, realistic:15  # bugs appear above 30
	'color': 'red',
}

animation_spec = {
	'fps':20,  # frames per second
}

def kmh2cps(kph):
	cm_per_km = 10000
	sec_per_hr = 3600
	cps = (kph * cm_per_km) / sec_per_hr
	return cps

def placeCones(arena, event):
	# build and return a 2D array of x,y points randomly positioned within the arena

	#constants
	min_dist_factor = 0.3
	starting_pool_size = 100
	margin_factor = 0.05

	#calculations
	margin = int(((arena['w'] + arena['h']) / 2) * margin_factor)
	min_dist = int(((arena['w'] + arena['h']) / 2) * min_dist_factor)
	
	# get a pool of points
	x = np.random.randint(low=margin, high=arena['w']-margin, size=(starting_pool_size,1), dtype=int)
	y = np.random.randint(low=margin, high=arena['h']-margin, size=(starting_pool_size,1), dtype=int)
	pool = np.transpose([x,y])[0]

	# elimate points until remaining points have a good spread
	j = 1 # count of good points
	while j < pool.shape[0]:
		ndx_for_deletion = []
		for i in range(j, pool.shape[0]):
			for h in range(0, j):
				d = math.dist(pool[h], pool[i]) 
				if d < min_dist:
					ndx_for_deletion.append(i) 
					break
		if len(ndx_for_deletion) > 0:
			pool = np.delete(pool, ndx_for_deletion, axis=0)
		j = j+1
	
	# choose final four
	pool = pool[:event['num_cones']]

	# center the cones in the arena
	tpool = np.transpose(pool)
	lo = np.array([tpool[0].min(), tpool[1].min()])
	hi = np.array([tpool[0].max(), tpool[1].max()]) 
	bbox_center = lo + ((hi - lo) / 2)
	arena_center = np.array([int(arena['w']/2), int(arena['h']/2)])
	adj = arena_center - bbox_center
	pool = np.add(pool,adj)

	cones = []
	for pt in pool:
		cones.append({
			'center':pt, 
		})
	
	return cones 
		
def chooseSides(cones):
	for cone in cones:
		rdir = np.random.choice(['ccw','cw'])
		cone['rdir'] = rdir
	return cones
	
def calcCones(cones, skate):
	# add entry and exit points to each cone
	r = skate['turning_radius']
	gate = { 'center': arena_spec['gate'] }
	for i in range(len(cones)):
		cone = cones[i]
		prevcone = gate if i <= 0 else cones[i-1]
		nextcone = gate if i+1 >= len(cones) else cones[i+1] 

		# entry point
		A = prevcone['center']
		B = cone['center']
		L, R = nav.linePerpendicular(A, B, r)
		entry = {
			'L': L,
			'R': R,
		}
	
		# exit point
		A = nextcone['center']
		B = cone['center']
		L, R = nav.linePerpendicular(A,B,r)
		exit = {
			'L': L,
			'R': R,
		}
	
		if cone['rdir'] == 'cw':
			cone['entry'] = entry['L']
			cone['exit']  = exit['R']
		else:
			cone['entry'] = entry['R']
			cone['exit']  = exit['L']
	return cones
	
def plotRoute(cones, skate):
	route = []
	gate = arena_spec['gate']
	prevexit = gate
	for i in range(0,len(cones)):
		cone = cones[i]
	
		heading = nav.headingOfLine(prevexit, cone['entry'])
	
		route.append({
			'shape': 'line',
			'from': prevexit,
			'to': cone['entry'],
			'bearing': heading,
		})
	
		route.append({
			'shape': 'arc',
			'from': cone['entry'],
			'to': cone['exit'],
			'center': cone['center'],
			'rdir': cone['rdir'],
		})
		
		prevexit = cone['exit']
	
	# back to starting gate
	heading = nav.headingOfLine(prevexit, gate)
	route.append({
		'shape': 'line',
		'from': prevexit,
		'to': gate,
		'bearing': heading,
	})
	return route

'''
drawing routines
'''

def drawRoute(route, arena, skate):
	radius = skate['turning_radius']
	color = arena['routecolor']
	for leg in route:
		if leg['shape'] == 'line':
			nav.drawLine([leg['from'], leg['to']], color)

		elif leg['shape'] == 'arc':
			tfrom,_ = nav.thetaFromPoint(leg['from'], leg['center'])
			tto,_   = nav.thetaFromPoint(leg['to']  , leg['center'])
			nav.drawArc(tfrom, tto, leg['rdir'], leg['center'], radius, color)

def drawArena(cones, arena, test=False):
	# draw cones
	color = arena['conecolor'] 
	radius = skate_spec['turning_radius']
	i = 0
	for cone in cones:
		pt = cone['center']
		i += 1
		plt.text( pt[0], pt[1], str(i), fontsize='14', ha='center', va='center', color=color)

		if test:
			#c = plt.Circle(pt, radius, fill=False); plt.gca().add_patch(c)
			nav.drawPoint(cone['entry'], color='green')
			nav.drawPoint(cone['exit'], color='red')

	# draw gate
	x,y = np.transpose(arena_spec['gate']); 
	plt.scatter(x,y, color=color)

	# draw frame
	plt.xlim(0,arena_spec['w'])
	plt.ylim(0,arena_spec['h'])
	plt.autoscale(False)
	plt.gca().set_aspect('equal', anchor='C')
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	plt.gca().spines['bottom'].set_color(color)
	plt.gca().spines['top'].set_color(color)
	plt.gca().spines['left'].set_color(color)
	plt.gca().spines['right'].set_color(color)

#--------------- above is library functions, below is animation, implemented as global -----------------# 

# a line2D artist object to represent the skate, used by FuncAnimation
color = skate_spec['color']
points_per_pixel = 4  # linewidth is given in "points"
lw = int(skate_spec['width'] / points_per_pixel)
skateline, = plt.gca().plot([], [], lw=lw, color=color)
skatedot,  = plt.gca().plot([], [], 'bo', markersize=4)

# animation variables
speed = kmh2cps(skate_spec['avgspeed'])
lastKnown = {
	'position': arena_spec['gate'],
	'heading': 0,
	'steering': 0,
}
legndx = 0

# animation constants
delay = int(1000 / animation_spec['fps']) # delay between frames in milliseconds

def nextLeg():
	global legndx, lastKnown
	legndx += 1
	if legndx >= len(route):
		legndx = 0
	if route[legndx]['shape'] == 'line':
		lastKnown['heading'] = route[legndx]['bearing']
		lastKnown['position'] = route[legndx]['from']
	return legndx

def plotSkate(): # based on position and heading
	# FuncAnimation does the drawing
	# here we calculate the x,y for the line object
	global lastKnown
	bow,stern = nav.lineFromHeading(lastKnown['position'], lastKnown['heading'], skate_spec['length'])
	return bow,stern

def positionSkate(framenum):
	global lastKnown
	shape = route[legndx]['shape']
	newpos = []
	distance = speed
	if shape == 'line':
		heading = lastKnown['heading']
		steering = lastKnown['steering']
		course = heading + steering
		newpos = nav.reckonLine(lastKnown['position'], course, distance)
		ispast = nav.isPointPastLine(route[legndx]['from'], route[legndx]['to'], newpos)
		if ispast:
			nextLeg()
		#newheading = based on newpos ?  actual heading is  visual on skate
		#steering = adjust based on relative bearing

	elif shape == 'arc':
		leg = route[legndx]
		tfrom,_ = nav.thetaFromPoint(leg['from'], leg['center'])
		tto,_   = nav.thetaFromPoint(leg['to'], leg['center'])
		center = leg['center']
		rdir = leg['rdir']
		radius = skate_spec['turning_radius']
		thetaOld,_ = nav.thetaFromPoint(lastKnown['position'],center)

		# hello? heading is not a factor in reckonArc
		thetaNew = nav.reckonArc(thetaOld, distance, radius, rdir)
		x,y = nav.pointFromTheta(center, thetaNew, radius)
		newpos = [x,y]

		newattitude = nav.linePerpendicular( center, newpos, radius)
		B,A = newattitude
		lastKnown['heading'] = nav.headingOfLine(A,B)

		ispast = nav.isThetaPastArc(tfrom,tto,thetaNew, center,radius, rdir)
		if ispast:
			nextLeg()
	return newpos

def init(): # called once before first frame, but in fact is called twice
	# set initial position of skateline
	global lastKnown, skateline, skatedot
	lastKnown['heading'] = route[0]['bearing']
	A,B = plotSkate()
	x,y = np.transpose([A,B])
	skateline.set_data(x,y)
	skatedot.set_data([A[0],A[1]])
	return # skatedot, skateline

def animate(framenum): # called once for every frame
	global skateline, skatedot, lastKnown
	lastKnown['position'] = positionSkate(framenum)
	A,B = plotSkate()
	x,y = np.transpose([A,B])
	skateline.set_data(x,y)
	skatedot.set_data([A[0],A[1]])
	return # skatedot, skateline # because blit=True, return a list of artists

if __name__ == '__main__':
	global runquiet
	runquiet = True
	logging.basicConfig(format='%(message)s')
	if not set(['--quiet', '-q']) & set(sys.argv):
		runquiet = False
		logging.getLogger('').setLevel(logging.INFO)

	# main
	cones = placeCones(arena_spec, event_spec)
	cones = chooseSides(cones)
	#cones = nav.conesfreestyle
	cones = nav.conestwobugs
	for cone in cones: logging.info(cone)

	cones = calcCones(cones, skate_spec)
	#for cone in cones: logging.info(cone)

	route = plotRoute(cones, skate_spec)
	drawArena(cones, arena_spec)
	drawRoute(route, arena_spec, skate_spec)
	#for leg in route: logging.info(str(leg['shape'] + '\t' + str(leg['from'])))
	
	anim = FuncAnimation(plt.gcf(), animate, init_func=init, frames=None, interval=delay, blit=False)
	
	plt.show()

