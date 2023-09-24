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
import json

# all measurements are in cm's, and 1 cm == 1 pixel
# speed is in kph, and internally changed to cps
# x,y pixel positions in the arena stand in for lng,lat coordinates

def kmh2cps(kph):
	cm_per_km = 10000
	sec_per_hr = 3600
	cps = (kph * cm_per_km) / sec_per_hr
	return cps

def placeCones():
	# build and return a 2D array of x,y points randomly positioned within the arena

	#constants
	min_dist_factor = 0.3
	starting_pool_size = 100
	margin_factor = 0.05

	#calculations
	margin = int(((spec.arenawidth + spec.arenaheight) / 2) * margin_factor)
	min_dist = int(((spec.arenawidth + spec.arenaheight) / 2) * min_dist_factor)
	
	# get a pool of points
	x = np.random.randint(low=margin, high=spec.arenawidth-margin, size=(starting_pool_size,1), dtype=int)
	y = np.random.randint(low=margin, high=spec.arenaheight-margin, size=(starting_pool_size,1), dtype=int)
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
	pool = pool[:spec.numcones]

	# center the cones in the arena
	tpool = np.transpose(pool)
	lo = np.array([tpool[0].min(), tpool[1].min()])
	hi = np.array([tpool[0].max(), tpool[1].max()]) 
	bbox_center = lo + ((hi - lo) / 2)
	arena_center = np.array([int(spec.arenawidth/2), int(spec.arenaheight/2)])
	adj = arena_center - bbox_center
	pool = np.add(pool,adj)

	cones = []
	for pt in pool:
		cones.append({
			'center':pt, 
		})
	
	#return cones 
	return pool 
		
def planRoute(cones):
	order = []
	for i in range(len(cones)):
		order.append(i)
	random.shuffle(order)
	
	sides = []
	for cone in cones:
		rdir = np.random.choice(['ccw','cw'])
		sides.append(rdir)
	return order, sides
	
def calcPlan(cones, order, sides):
	# combine cones, order, sides into a list of dicts, sorted by order
	plan = []
	for i in range(len(cones)):
		plan.append({
			'order':order[i], 
			'center':cones[i], 
			'rdir':sides[i], 
		})
	plan = sorted(plan, key=lambda cone: cone['order'])

	# add entry and exit points to each cone
	r = spec.turningradius
	gate = { 'center': (spec.gatex,spec.gatey) }
	for i in range(len(plan)):
		cone = plan[i]
		prevcone = gate if i <= 0 else plan[i-1]
		nextcone = gate if i+1 >= len(plan) else plan[i+1] 

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
	return plan
	
def plotRoute(plan):
	route = []
	gate = (spec.gatex,spec.gatey)
	prevexit = gate
	for i in range(0,len(plan)):
		cone = plan[i]

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

def drawRoute(route, test=True):
	radius = spec.turningradius
	color = spec.routecolor
	for leg in route:
		if leg['shape'] == 'line':
			nav.drawLine([leg['from'], leg['to']], color)

		elif leg['shape'] == 'arc':
			tfrom,_ = nav.thetaFromPoint(leg['from'], leg['center'])
			tto,_   = nav.thetaFromPoint(leg['to']  , leg['center'])
			nav.drawArc(tfrom, tto, leg['rdir'], leg['center'], radius, color)

def drawArena(plan, test=False):
	# draw cones
	color = spec.conecolor 
	radius = spec.turningradius
	i = 0
	for cone in plan:
		pt = cone['center']
		i += 1
		plt.text( pt[0], pt[1], str(i), fontsize='14', ha='center', va='center', color=color)

		if test:
			#c = plt.Circle(pt, radius, fill=False); plt.gca().add_patch(c)
			nav.drawPoint(cone['entry'], color='green')
			nav.drawPoint(cone['exit'], color='red')

	# draw gate
	nav.drawPoint((spec.gatex,spec.gatey), color=color)

	# draw frame
	plt.xlim(0,spec.arenawidth)
	plt.ylim(0,spec.arenaheight)
	plt.autoscale(False)
	plt.gca().set_aspect('equal', anchor='C')
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	plt.gca().spines['bottom'].set_color(color)
	plt.gca().spines['top'].set_color(color)
	plt.gca().spines['left'].set_color(color)
	plt.gca().spines['right'].set_color(color)

#--------------- above is library functions, below is animation, implemented as global -----------------# 

# global Artist objects displayed by FuncAnimation
skateline = plt.gca().scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])
trailline = plt.gca().scatter([0,0,0,0,0],[0,0,0,0,0], c='pink', s=2)
trailpoints = []

# globals
spec = None
cones = []
route = []
legn = 0
running = True
delay = 0

# global piloting variables
lastKnown = {
	'position': (0,0),
	'prevpos' : (0,0),
	'heading': 0,
	'course': 0,
	'bearing': 0,
	'helm': 0,
	'speed': 0,
}

# global constants
dirvideoout = 'videos'
dirsavegame = 'games'

def nextLeg():
	global legn
	global running
	legn += 1
	if legn >= len(route): 
		if spec.videoout != 'none':
			running = False
		legn = 0
	if spec.verbose and not spec.quiet:
		logging.info(f'begin leg {legn}: {route[legn]["shape"]}')
	return legn

def plotSkate(): # based on position and heading
	global skateline # lastKnown
	bow,stern = nav.lineFromHeading(lastKnown['position'], lastKnown['heading'], spec.skatelength)
	diff = (bow - stern) / 5  # add 4 dots between bow and stern
	points = [0,0,0,0,0]
	for i in range(5): points[i] = stern + (diff * i)
	skateline.set_offsets(points) # FuncAnimation does the drawing

	if spec.trail != 'none':
		trailpoints.append(lastKnown['prevpos'])
		trailline.set_offsets(trailpoints)
	return bow,stern

def getPositionFromCamera():
	return False,0

def addRandomDrift(pos):
	p = pos
	rx = (random.random() * 2 - 1) * spec.drift
	ry = (random.random() * 2 - 1) * spec.drift
	p = pos + np.array([rx,ry])
	return p

def getPosition(fnum):
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
			if spec.simmode == 'precise':
				newpos = route[legn]['from']
				if route[legn]['shape'] == 'line':
					head = route[legn]['bearing']

	elif leg['shape'] == 'arc':
		tfrom,_ = nav.thetaFromPoint(leg['from'], leg['center'])
		tto,_   = nav.thetaFromPoint(leg['to'], leg['center'])
		center = leg['center']
		rdir = leg['rdir']
		radius = spec.turningradius
		thetaOld,_ = nav.thetaFromPoint(lastKnown['position'],center)

		# hello? heading is not a factor in reckonArc
		thetaNew = nav.reckonArc(thetaOld, distance, radius, rdir)
		x,y = nav.pointFromTheta(center, thetaNew, radius)
		newpos = [x,y]

		# re-orient the skate as it rotates around the cone
		if spec.simmode == 'precise':
			perp = nav.linePerpendicular( center, newpos, radius)
			if rdir == 'cw': A,B = perp	
			else: B,A = perp
			head = nav.headingOfLine(A,B)

		ispast = nav.isThetaPastArc(tfrom,tto,thetaNew, center,radius, rdir)
		fractional = nav.lengthOfArc(tto, thetaNew, radius, rdir) < distance
		if ispast or fractional:
			nextLeg()
			if spec.simmode == 'precise': 
				newpos = route[legn]['from']
				head = route[legn]['bearing']

	if spec.simmode == 'helmed':
		savpos = newpos
		newpos = addRandomDrift(newpos)

	if spec.simmode == 'helmed':
		head = nav.headingOfLine(lastKnown['prevpos'], newpos)
	return newpos,head

def clamp(num, min_value, max_value):
	return max(min(num, max_value), min_value)

def setHelm():
	heading = lastKnown['heading']
	newbearing = nav.headingOfLine( lastKnown['position'], route[legn]['to'])
	if newbearing < 0:
		newbearing += 360

	relative_bearing = newbearing - heading
	if relative_bearing > 180:
		relative_bearing = newbearing - (heading + 360)	
	if relative_bearing < -180:
		relative_bearing = newbearing + (heading - 360)	

	helm = relative_bearing * (spec.helmpct / 100)
	helm = clamp(helm, 0-spec.helmrange, spec.helmrange)
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

def animate(fnum): # called once for every frame
	global skateline, lastKnown
	if fnum > (spec.startdelay / 1000) * spec.fps: 
		lastKnown['prevpos'] = lastKnown['position']
		lastKnown['position'], lastKnown['heading'] = getPosition(fnum)
		lastKnown['bearing'] = getBearing()
		if spec.simmode == 'helmed':
			lastKnown['helm'] = setHelm()
			lastKnown['speed'] = setThrottle()
	
	A,B = plotSkate()
	return skateline, trailline # when blit=True, return a list of artists

def gen(): # generate a sequential frame count, with a kill switch
	global running
	global framenum
	framenum = 0
	while running:
		yield framenum
		framenum += 1

def flattenCones(d2):
	a = []
	for r in d2:
		a.append(r[0])
		a.append(r[1])
	return a

def unflattenCones(flat):
	d2 = []
	i = 0
	while i < len(flat):
		x = flat[i]
		y = flat[i+1]	
		d2.append((x,y))
		i += 2
	return d2
def writeGame(cones,order,sides):
	speca = vars(spec)
	flat = flattenCones(cones)
	savedgame = {
		'speca': speca,
		'flat' : flat,
		'order': order,
		'sides': sides,
	}
	#json_string = json.dumps(savedgame)
	fh = open(f'{dirsavegame}/{spec.savegame}.json', 'w')
	#json.dump(json_string, fh)
	json.dump(savedgame, fh)

def readGame():
	global spec
	fh = open(f'{dirsavegame}/{spec.game}.json', 'r')
	savedgame = json.load(fh)
	print(savedgame)
	speca = savedgame['speca']
	flat  = savedgame['flat']
	order = savedgame['order']
	sides = savedgame['sides']

	spec = argparse.Namespace(**speca)
	cones = unflattenCones(flat)
	
	return cones, order, sides

event_names = [
	'freestyle',
	'barrel-racing',
	'course-racing',
	'straight-line-slalom',
	'downhill-slalom',
	'spiral',
]
game_names = [
	'firstgame',
]

def main():
	global spec, cones, route, delay, lastKnown

	# args

	parser = argparse.ArgumentParser()

	# event spec, provided by operator
	parser.add_argument('-e'  , '--event'		,default='freestyle'	,choices=event_names			,help='name of event'			),

	# arena spec, normally supplied by camera
	parser.add_argument('-aw' , '--arenawidth'	,default=4000		,type=int				,help='width of arena in pixels'	),
	parser.add_argument('-ah' , '--arenaheight'	,default=4000		,type=int				,help='height of arena in pixels'	),
	parser.add_argument('-gx' , '--gatex'		,default=2000		,type=int				,help='x position of starting gate'	),
	parser.add_argument('-gy' , '--gatey'		,default=50		,type=int				,help='y position of starting gate'	),

	# sim spec, used only by the simulator
	parser.add_argument('-sm' , '--simmode'		,default='precise'	,choices=['none','precise', 'helmed']	,help='simulation mode'			),
	parser.add_argument('-d'  , '--drift'		,default=0		,type=int				,help='maximum random drift in degrees'	), 
	parser.add_argument('-nc' , '--numcones'	,default=5		,type=int				,help='number of cones'			),

	# skate spec, unique to each skate, maybe determined by machine learning
	parser.add_argument('-tr' , '--turningradius'	,default=200		,type=int				,help='skate turning radius'		),
	parser.add_argument('-sl' , '--skatelength'	,default=70		,type=int				,help='skate length in cm'		),
	parser.add_argument('-sw' , '--skatewidth'	,default=20		,type=int				,help='skate width in cm'		),
	parser.add_argument('-sc' , '--skatecolor'	,default='red'							,help='skate color'			),
	parser.add_argument('-as' , '--avgspeed'	,default=15		,type=int				,help='average speed'			),
	parser.add_argument('-hl' , '--helmlag'		,default=0		,type=int				,help='lag before helm takes effect'	),
	parser.add_argument('-hp' , '--helmpct'		,default=30		,type=int				,help='percent of relative bearing'	),
	parser.add_argument('-hr' , '--helmrange'	,default=45		,type=int				,help='range of helm in degrees =/-'	),

	# run spec, having to do only with the computer and operator
	parser.add_argument('-q'  , '--quiet'		,default=False		,action='store_true'			,help='run without console messages'	),
	parser.add_argument('-v'  , '--verbose'		,default=False		,action='store_true'			,help='show detailed console messages'	),
	parser.add_argument('-g'  , '--game'		,default='none'					,help='filename of saved game'		),
	parser.add_argument('-t'  , '--trail'		,default='none'		,choices=['none', 'full', 'lap']	,help='trail left by skate'		), 
	parser.add_argument('-o'  , '--videoout'	,default='none'							,help='filename for video output'	),
	parser.add_argument('-sg' , '--savegame'	,default='none'							,help='filename for game to save'	),
	parser.add_argument('-f'  , '--fps'		,default=20		,type=int				,help='frames per second'		),
	parser.add_argument('-sd' , '--startdelay'	,default=1000		,type=int				,help='delay milliseconds before start' ),
	parser.add_argument('-cc' , '--conecolor'	,default='cyan'							,help='color of cones'			),
	parser.add_argument('-rc' , '--routecolor'	,default='black'						,help='color of route'			),

	spec = parser.parse_args()	# returns Namespace object, use dot-notation

	# logging

	logging.basicConfig(format='%(message)s')
	if not spec.quiet:
		logging.getLogger('').setLevel(logging.INFO)

	# more args

	speca = vars(spec)		# returns iterable and subscriptable collection
	for k in speca:
		tab = '\t' if len(k) >= 8 else '\t\t'
		logging.info(f'{k}{tab}{speca[k]}')

	# initialization	

	lastKnown['position'] = (spec.gatex,spec.gatey)
	lastKnown['prevpos'] = (spec.gatex,spec.gatey)
	lastKnown['speed'] = kmh2cps(spec.avgspeed)
	delay = int(1000 / spec.fps) # delay between frames in milliseconds

	# sim setup

	if spec.videoout == 'none':
		save_count = None
		repeat = True
	else:
		save_count = 2000
		repeat = False

	# saved game

	if spec.game != 'none':
		cones, order, sides = readGame()

	# setup arena -&- plan route

	if len(cones) == 0:
		cones = placeCones()
		order,sides = planRoute(cones)

	for cone in cones: logging.info(cone)
	logging.info(order)
	logging.info(sides)

	# more saved game

	if spec.savegame != 'none':
		writeGame(cones,order,sides)

	# plan next lap

	plan = calcPlan(cones, order, sides)
	route = plotRoute(plan)
	drawArena(plan)
	drawRoute(route)

	# more initialization

	if spec.simmode == 'precise':
		lastKnown['heading'] = route[0]['bearing']
	
	# main loop

	anim = FuncAnimation(plt.gcf(), animate, frames=gen, repeat=repeat, save_count=save_count, interval=delay, blit=True)

	# save or show

	if spec.videoout == 'none':
		plt.show()
	else:
		anim.save(f'{dirvideoout}/{spec.videoout}.mp4')

	logging.info(f'Complete.  Num frames: {framenum}')

if __name__ == '__main__':
	main()

'''
brain parts
  - visualcortex
  - hippocampus
  - frontalcortex
  - drone (eyes and neck)

tasks of each brain part, shown below in sensoryMotorCircuit

main
  - wakeup
  - act while awake
    - sensoryMotorCircuit
      - drone.getFrame()
      - visualcortex.detectObjects
      - hippocampus.buildMap
      - frontalcortex.navigate
  - sleep

modify
  - add micropersonalities
  - separate navigator and pilot
  - simultaneously navigate and pilot, drone and skate
  - do other things besides running in an event (drone not necessary for these)
    - walk to and fro the event, remote-controlled by human operator 
    - train
      - run patterns over and over, improving for speed
      - setup imaginary arenas and run repeatedly for speed
    - play
      - compete skate vs drone
    - converse with human operator
  - add pleasure/pain centers
    - hunger for battery charge, drone and skate (bms)
      - must request assistance from human operator
    - detect battery full (charging controller)
  - act loop, sleep loop
  - four loops
    - drone nav
    - drone pilot
    - skate nav
    - skate pilot

engage in an activity
  - add one or more processes
  - each actor is a micropersonality
      - captain, pilot, navigator
      - an activity resembles a group converstaion or meeting

'''
