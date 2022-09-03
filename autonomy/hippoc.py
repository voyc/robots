''' hippoc.py '''

import numpy as np
import matplotlib.pyplot as plt  
import matplotlib  
import mpmath  
import math
import nav
from matplotlib.animation import FuncAnimation 
import sys
import logging
import argparse
import random
import time

# all measurements are in cm's, and 1 cm == 1 pixel
# speed is in kph, and internally changed to cps
# x,y pixel positions in the arena stand in for lng,lat coordinates

# global read-only specifications
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
	'helmrange': [-100,100],
	'length': 140, # 70,
	'width':  20,
	'avgspeed': 45, # kmh, realistic:15  # bugs appear above 30
	'color': 'red',
	'helmlag': 0,
	'helmpct': .30,
	'helmrange': [0,0],
	'drift': 30,
}

run_spec = {
	'quiet': False,
	'fps':20,         # frames per second
	'simmode': None,  # precise, helmed
	'startdelay': 1000,
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

#--------------- drawing ----------------------------------------# 

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
	nav.drawPoint(arena_spec['gate'], color=color)

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

# a line2D artist object to represent the skate, displayed by FuncAnimation
skateline = plt.gca().scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])

# driving variables
lastKnown = {
	'position': arena_spec['gate'],
	'prevpos' : arena_spec['gate'],
	'heading': 0,
	'course': 0,
	'bearing': 0,
	'helm': 0,
	'speed': kmh2cps(skate_spec['avgspeed']),
}

# globals
cones = []
route = []
legn = 0
running = True

# animation constants
delay = int(1000 / run_spec['fps']) # delay between frames in milliseconds

def nextLeg():
	global legn
	global running
	legn += 1
	if legn >= len(route): 
		running = False
		legn = 0
	return legn

def plotSkate(): # based on position and heading
	global skateline # lastKnown
	bow,stern = nav.lineFromHeading(lastKnown['position'], lastKnown['heading'], skate_spec['length'])
	diff = (bow - stern) / 5  # add 4 dots between bow and stern
	points = [0,0,0,0,0]
	for i in range(5): points[i] = stern + (diff * i)
	skateline.set_offsets(points) # FuncAnimation does the drawing
	return bow,stern

def getPositionFromCamera():
	return False,0

def addRandomDrift(pos):
	p = pos
	rx = (random.random() * 2 - 1) * skate_spec['drift']
	ry = (random.random() * 2 - 1) * skate_spec['drift']
	p = pos + np.array([rx,ry])
	return p

def getPosition(framenum):
	pos,head = getPositionFromCamera()
	if not pos:
		pos,head = getPositionByDeadReckoning()
	return pos,head

def getPositionByDeadReckoning():
	newpos = []
	head = lastKnown['heading']
	helm = lastKnown['helm']
	leg = route[legn]
	distance = lastKnown['speed']
	if leg['shape'] == 'line':
		newpos = nav.reckonLine(lastKnown['position'], head+helm, distance)
		ispast = nav.isPointPastLine(leg['from'], leg['to'], newpos)
		if ispast:
			nextLeg()
			if run_spec['simmode'] == 'precise':
				newpos = route[legn]['from']
				if route[legn]['shape'] == 'line':
					head = route[legn]['bearing']

	elif leg['shape'] == 'arc':
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

		# re-orient the skate as it rotates around the cone
		if run_spec['simmode'] == 'precise':
			perp = nav.linePerpendicular( center, newpos, radius)
			if rdir == 'cw': A,B = perp	
			else: B,A = perp
			head = nav.headingOfLine(A,B)

		ispast = nav.isThetaPastArc(tfrom,tto,thetaNew, center,radius, rdir)
		fractional = nav.lengthOfArc(tto, thetaNew, radius, rdir) < distance
		if ispast or fractional:
			nextLeg()
			if run_spec['simmode'] == 'precise': 
				newpos = route[legn]['from']
				head = route[legn]['bearing']

	if run_spec['simmode'] == 'helmed':
		savpos = newpos
		newpos = addRandomDrift(newpos)

	head = nav.headingOfLine(lastKnown['prevpos'], newpos)
	return newpos,head

def setHelm():
	#course = lineFromHeading(from prev posiion to current position
	#bearing = headingFromLine(from position to leg.to
	#relative = bearing - course
	#helm = a percentage of relative bearing
	helmmin = skate_spec['helmrange'][0]
	helmmax = skate_spec['helmrange'][1]

	heading = lastKnown['heading']
	newbearing = nav.headingOfLine( lastKnown['position'], route[legn]['to'])
	if newbearing < 0:
		newbearing += 360
	helmpct = skate_spec['helmpct']

	relative_bearing = newbearing - heading
	if abs(relative_bearing) > 180:
		relative_bearing = newbearing - (heading + 360)	

	helm = relative_bearing * helmpct
	return helm

def setThrottle():
	return lastKnown['speed']

def getBearing():
	bearing = False	
	if route[legn]['shape'] == 'line':
		bearing = route[legn]['bearing']
	else:
		bearing = route[legn+1]['bearing']
	return bearing

def animate(framenum): # called once for every frame
	global skateline, lastKnown
	if framenum > (run_spec['startdelay'] / 1000) * 20: 
		lastKnown['prevpos'] = lastKnown['position']
		lastKnown['position'], lastKnown['heading'] = getPosition(framenum)
		lastKnown['bearing'] = getBearing()
		if run_spec['simmode'] == 'helmed':
			lastKnown['helm'] = setHelm()
			lastKnown['speed'] = setThrottle()
	
	A,B = plotSkate()
	return skateline, # when blit=True, return a list of artists

def gen():
	global running
	num = 0
	while running:
		yield num
		num += 1

if __name__ == '__main__':
	# get arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('-q', '--quiet', help='run without console messages', action='store_true')
	parser.add_argument('-sm', '--simmode', help='simulation mode', choices=['precise', 'helmed'], default='precise')
	parser.add_argument('-o', '--output', help='simulation mode', default='none')
	args = parser.parse_args()
	run_spec['quiet'] = args.quiet
	run_spec['simmode'] = args.simmode

	logging.basicConfig(format='%(message)s')
	if not run_spec['quiet']:
		logging.getLogger('').setLevel(logging.INFO)

	logging.info(f'simmode {run_spec["simmode"]}') 

	# main
	cones = placeCones(arena_spec, event_spec)
	cones = chooseSides(cones)

	#cones = nav.conesfreestyle
	#cones = nav.conestwobugs
	#cones = nav.conespassby
	for cone in cones: logging.info(cone)

	cones = calcCones(cones, skate_spec)

	route = plotRoute(cones, skate_spec)

	drawArena(cones, arena_spec)
	drawRoute(route, arena_spec, skate_spec)

	if run_spec['simmode'] == 'precise':
		lastKnown['heading'] = route[0]['bearing']

	anim = FuncAnimation(plt.gcf(), animate, frames=gen, repeat=False, save_count=2000, interval=delay, blit=True)

	if args.output == 'none':
		plt.show()
	else:
		anim.save(args.output)

'''
'''
