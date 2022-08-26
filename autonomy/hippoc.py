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
# x,y pixel positions in the arena are stand-ins for lng,lat coordinates

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
	'avgspeed': 15, # kmh, realistically... 15
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
		thetaL,_ = nav.thetaFromPoint(L,B)
		thetaR,_ = nav.thetaFromPoint(R,B)
		entry = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		# exit point
		A = nextcone['center']
		B = cone['center']
		L, R = nav.linePerpendicular(A,B,r)
		thetaL,_ = nav.thetaFromPoint(L,B)
		thetaR,_ = nav.thetaFromPoint(R,B)
		exit = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		cone['entry'] = entry
		cone['exit'] = exit

		if cone['rdir'] == 'cw':
			cone['entrypoint'] = cone['entry']['L']
			cone['exitpoint'] = cone['exit']['R']
			cone['entrytheta'] = cone['entry']['thetaL']
			cone['exittheta'] = cone['exit']['thetaR']
		else:
			cone['entrypoint'] = cone['entry']['R']
			cone['exitpoint'] = cone['exit']['L']
			cone['entrytheta'] = cone['entry']['thetaR']
			cone['exittheta'] = cone['exit']['thetaL']
	return cones
	
def buildRoute(cones, skate):
	route = []
	gate = arena_spec['gate']
	prevexitpoint = gate
	for i in range(0,len(cones)):
		cone = cones[i]
	
		#if cone['rdir'] == 'cw':  # CW L to R (Arc always goes CCW)
		#	theta1 = cone['entry']['thetaL']
		#	theta2 = cone['exit']['thetaR'] 
		#	entrypoint = cone['entry']['L']
		#	exitpoint = cone['exit']['R']
		#else:  # CCW R to L
		#	theta1 = cone['entry']['thetaR']
		#	theta2 = cone['exit']['thetaL']
		#	entrypoint = cone['entry']['R']
		#	exitpoint = cone['exit']['L']
	
		heading = nav.headingOfLine(prevexitpoint, cone['entrypoint'])
	
		route.append({
			'shape': 'line',
			'from': prevexitpoint,
			'to': cone['entrypoint'],
			'heading': heading,
		})
	
		route.append({
			'shape': 'arc',
			'from': cone['entrytheta'],
			'to': cone['exittheta'],
			'center': cone['center'],
			'rdir': cone['rdir'],
		})
		
		prevexitpoint = cone['exitpoint']
	
	# back to starting gate
	heading = nav.headingOfLine(prevexitpoint, gate)
	route.append({
		'shape': 'line',
		'from': prevexitpoint,
		'to': gate,
		'heading': heading,
	})
	return route

'''
drawing routines
'''
def drawPoint(pt, color='black'): 
	x,y = np.transpose(pt); 
	plt.scatter(x,y,color=color)

def drawLine(line, color='black'): 
	x,y = np.transpose(line); 
	plt.plot(x,y, color=color, lw=1)

def drawArc(pt, r, theta1, theta2, rdir, color='black'): 
	color = 'red'
	t1 = theta1
	t2 = theta2
	if rdir == 'cw': 
		t1 = theta2
		t2 = theta1
	a = matplotlib.patches.Arc(pt, r*2, r*2, 0, math.degrees(t1), math.degrees(t2), color=color)
	plt.gca().add_patch(a)

def drawRoute(route, arena, skate):
	radius = skate['turning_radius']
	color = arena['routecolor']
	for leg in route:
	
		#drawLine([cone['entry']['R'], cone['entry']['L']], 'green')
		#drawLine([cone['exit']['R'], cone['exit']['L']], 'red')
		#drawPoint(entrypoint, color='green')
		#drawPoint(exitpoint, color='red')
	
		if leg['shape'] == 'line':
			drawLine([leg['from'], leg['to']], color)

		elif leg['shape'] == 'arc':
			drawArc(leg['center'], radius, leg['from'], leg['to'], leg['rdir'], color)

def drawArena(cones, arena):
	# draw cones
	color = arena['conecolor'] 
	radius = skate_spec['turning_radius']
	i = 0
	for cone in cones:
		pt = cone['center']
		i += 1
		plt.text( pt[0], pt[1], str(i), fontsize='14', ha='center', va='center', color=color)

		#c = plt.Circle(pt, radius, fill=False); plt.gca().add_patch(c)

		drawPoint(cone['entrypoint'], color='green')
		drawPoint(cone['exitpoint'], color='red')

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
points_per_pixel = 4  # linewidth is given in "points", officially 7
lw = int(skate_spec['width'] / points_per_pixel)
skateline, = plt.gca().plot([], [], lw=lw, color=color)

# animation variables
speed = kmh2cps(skate_spec['avgspeed'])
lastKnownPosition = arena_spec['gate']
lastKnownHeading = 318 # compass heading
lastKnownSteeringAngle = 0 # relative bearing2
legndx = 0

# animation constants
delay = int(1000 / animation_spec['fps']) # delay between frames in milliseconds

def nextLeg():
	global legndx, lastKnownPosition, lastKnownHeading
	legndx += 1
	if legndx >= len(route):
		legndx = 0
	if route[legndx]['shape'] == 'line':
		lastKnownHeading = route[legndx]['heading']
		lastKnownPosition = route[legndx]['from']
	return legndx

def plotSkate(): # based on position and heading
	# FuncAnimation does the drawing
	# here we calculate the x,y for the line object
	global lastKnownPosition, lastKnownHeading
	bow,stern = nav.lineFromHeading(lastKnownPosition, lastKnownHeading, skate_spec['length'])
	x,y = np.transpose([stern, bow])
	return x,y

counter = 0

def positionSkate(framenum):
	global lastKnownPosition, lastKnownHeading
	shape = route[legndx]['shape']
	newpos = []
	distance = speed
	if shape == 'line':
		start = route[legndx]['from']
		end = route[legndx]['to']
		newpos = nav.reckon(lastKnownPosition, lastKnownHeading, distance)
		ispast = nav.isPointPast(start, end, newpos)
		if ispast:
			nextLeg()
			newpos = nav.reckon(lastKnownPosition, lastKnownHeading, speed)
	elif shape == 'arc':
		radius = skate_spec['turning_radius']
		center = route[legndx]['center']
		rdir = route[legndx]['rdir']
		x,y = np.transpose(lastKnownPosition)
		theta1 = nav.thetaFromPoint(x,y,center,radius)
		theta2 = nav.reckonArc(theta1, distance, radius, rdir)
		x,y = nav.xyFromTheta(center, theta2, radius)
		newpos = [x,y]
		global counter
		counter += 1
		#if counter >= 10: quit()
	return newpos

def init(): # called once before first frame, but in fact is called twice
	# set initial position of skateline
	global skateline
	x,y = plotSkate()
	skateline.set_data(x, y)
	return skateline,

def animate(framenum): # called once for every frame
	global skateline, lastKnownPosition
	lastKnownPosition = positionSkate(framenum)
	x,y = plotSkate()
	skateline.set_data(x, y)
	return skateline, # because blit=True, return a list of artists

if __name__ == '__main__':
	global runquiet
	runquiet = True
	if not set(['--quiet', '-q']) & set(sys.argv):
		runquiet = False
		logging.getLogger('').setLevel(logging.INFO)

	# main
	cones = placeCones(arena_spec, event_spec)
	cones = chooseSides(cones)
	cones = calcCones(cones, skate_spec)
	route = buildRoute(cones, skate_spec)
	drawArena(cones, arena_spec)
	drawRoute(route, arena_spec, skate_spec)
	
	#anim = FuncAnimation(plt.gcf(), animate, init_func=init, frames=None, interval=delay, blit=True)
	 
	#logging.info(cones)
	for cone in cones: logging.info(str(cone['center']) + '\t' + cone['rdir'])
	for leg in route: logging.info(leg)
	
	plt.show()

