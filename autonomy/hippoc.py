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
	
	return cones 
		
def chooseSides(cones):
	for cone in cones:
		rdir = np.random.choice(['ccw','cw'])
		cone['rdir'] = rdir
	return cones
	
def calcCones(cones):
	# add entry and exit points to each cone
	r = spec.turningradius
	gate = { 'center': (spec.gatex,spec.gatey) }
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
	
def plotRoute(cones):
	route = []
	gate = (spec.gatex,spec.gatey)
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

def drawRoute(route):
	radius = spec.turningradius
	color = spec.routecolor
	for leg in route:
		if leg['shape'] == 'line':
			nav.drawLine([leg['from'], leg['to']], color)

		elif leg['shape'] == 'arc':
			tfrom,_ = nav.thetaFromPoint(leg['from'], leg['center'])
			tto,_   = nav.thetaFromPoint(leg['to']  , leg['center'])
			nav.drawArc(tfrom, tto, leg['rdir'], leg['center'], radius, color)

def drawArena(cones, test=False):
	# draw cones
	color = spec.conecolor 
	radius = spec.turningradius
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

# Artist objects displayed by FuncAnimation
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

# piloting variables
lastKnown = {
	'position': (0,0),
	'prevpos' : (0,0),
	'heading': 0,
	'course': 0,
	'bearing': 0,
	'helm': 0,
	'speed': 0,
}

def nextLeg():
	global legn
	global running
	legn += 1
	if legn >= len(route): 
		if spec.output != 'none':
			running = False
		legn = 0
	if not spec.quiet:
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

event_names = [
	'freestyle',
	'barrel-racing',
	'course-racing',
	'straight-line-slalom',
	'downhill-slalom',
	'spiral',
]

def main():
	global spec, cones, route, delay, lastKnown

	parser = argparse.ArgumentParser()

	# arena spec
	parser.add_argument('-aw' , '--arenawidth'	,default=4000		,type=int				,help='width of arena in pixels'	),
	parser.add_argument('-ah' , '--arenaheight'	,default=4000		,type=int				,help='height of arena in pixels'	),
	parser.add_argument('-gx' , '--gatex'		,default=2000		,type=int				,help='x position of starting gate'	),
	parser.add_argument('-gy' , '--gatey'		,default=50		,type=int				,help='y position of starting gate'	),

	# sim spec
	parser.add_argument('-q'  , '--quiet'		,default=False		,action='store_true'			,help='run without console messages'	),
	parser.add_argument('-v'  , '--verbose'		,default=False		,action='store_true'			,help='show detailed console messages'	),
	parser.add_argument('-sm' , '--simmode'		,default='precise'	,choices=['precise', 'helmed']		,help='simulation mode'			),
	parser.add_argument('-d'  , '--drift'		,default=0		,type=int				,help='maximum drift in degrees'	), 
	parser.add_argument('-td' , '--suite'		,default='none'		,choices=['','']			,help='name of test data suite'		),

	# run spec
	parser.add_argument('-t'  , '--trail'		,default='none'		,choices=['none', 'full', 'lap']	,help='trail left by skate'		), 
	parser.add_argument('-o'  , '--output'		,default='none'							,help='output filename'			),
	parser.add_argument('-f'  , '--fps'		,default=20		,type=int				,help='frames per second'		),
	parser.add_argument('-sd' , '--startdelay'	,default=1000		,type=int				,help='delay milliseconds before start' ),
	parser.add_argument('-cc' , '--conecolor'	,default='cyan'							,help='color of cones'			),
	parser.add_argument('-rc' , '--routecolor'	,default='black'						,help='color of route'			),

	# event spec
	parser.add_argument('-e'  , '--event'		,default='freestyle'	,choices=event_names			,help='name of event'			),
	parser.add_argument('-nc' , '--numcones'	,default=5		,type=int				,help='number of cones'			),

	# skate spec
	parser.add_argument('-tr' , '--turningradius'	,default=200		,type=int				,help='skate turning radius'		),
	parser.add_argument('-sl' , '--skatelength'	,default=70		,type=int				,help='skate length in cm'		),
	parser.add_argument('-sw' , '--skatewidth'	,default=20		,type=int				,help='skate width in cm'		),
	parser.add_argument('-sc' , '--skatecolor'	,default='red'							,help='skate color'			),
	parser.add_argument('-as' , '--avgspeed'	,default=15		,type=int				,help='average speed'			),
	parser.add_argument('-hl' , '--helmlag'		,default=0		,type=int				,help='lag before helm takes effect'	),
	parser.add_argument('-hp' , '--helmpct'		,default=30		,type=int				,help='percent of relative bearing'	),
	parser.add_argument('-hr' , '--helmrange'	,default=45		,type=int				,help='range of helm in degrees =/-'	),

	spec = parser.parse_args()	# returns Namespace object, use dot-notation

	logging.basicConfig(format='%(message)s')
	if not spec.quiet:
		logging.getLogger('').setLevel(logging.INFO)

	speca = vars(spec)		# returns iterable and subscriptable collection
	for k in speca:
		tab = '\t' if len(k) >= 8 else '\t\t'
		logging.info(f'{k}{tab}{speca[k]}')

	lastKnown['position'] = (spec.gatex,spec.gatey)
	lastKnown['prevpos'] = (spec.gatex,spec.gatey)
	lastKnown['speed'] = kmh2cps(spec.avgspeed)
	delay = int(1000 / spec.fps) # delay between frames in milliseconds
	print(lastKnown)
	print(delay)

	if spec.suite != 'none':
		cones = nav.testcones[spec.suite]

	if spec.output == 'none':
		save_count = None
		repeat = True
	else:
		save_count = 2000
		repeat = False

	if len(cones) == 0:
		cones = placeCones()
		cones = chooseSides(cones)
	for cone in cones: logging.info(cone)

	cones = calcCones(cones)
	route = plotRoute(cones)
	drawArena(cones)
	drawRoute(route)

	if spec.simmode == 'precise':
		lastKnown['heading'] = route[0]['bearing']
	
	anim = FuncAnimation(plt.gcf(), animate, frames=gen, repeat=repeat, save_count=save_count, interval=delay, blit=True)

	if spec.output == 'none':
		plt.show()
	else:
		anim.save(f'output/{spec.output}.mp4')

	logging.info(f'Complete.  Num frames: {framenum}')

if __name__ == '__main__':
	main()

'''
keep helm within turning radius
	how to convert turning_radius to min/max relative_bearing
	can you do a unit test, circling a skate around a cone
		too tight, it collapses into the cone
		too loose, it spirals off the page
	slow down for tight turns
	gradually speed up with each iteration

named patterns:
	spiral
	freestyle
	slalom: straighti-line or course
	barrel race
	porch mandala
	perimeter
	slalom around the perimeter
	unit test named patterns, ie spiral
		run main and sim loop
		x leave a trail
		save image and compare image to referencd

repeat and timing each run
	barrel racing: run once and out
	freestyle: route, run, repeat, until what
	spiral: plot route, same cone again and again
	add lap counter
	frames, laps, elapsed, top speed
	start time, log with timer
	display all specs
	numlaps = 1

spiral pattern
	only one cone in dead center, run a spiral around it, within the arena boundaries
	no route, just forever circle one cone; gate, cone, gate
	add reverse
	find the centermost cone and spiral around it
	how to plot a route?  cannot.  has to be done at execution time
		cone center
		largest circle within arena given center
		smallest radius
		largest radius
		number of circles
		gradually increasing radius
	make spiral a leg shape
		given: center, start radius, end radius, radial pct increase radius each frame
			direction, in or out, cw or ccw
		any arc could be treated as a spiral, i
			with additional parameters
				number of passes
				radial change per frame
			set by plotRoute
			can a spiral intersect another cone?
				the spiral leg could be used like a line, as a route to the next cone

place cones per event
	freestyle
	barrel racing
	course racing
	straight line slalom
	downhill slalom
	spiral

notes:
	random options cannot be used for unittests
	plot route as you go, ala billiards
	how many cones?  if event = barrel racing, find valid barrels and ignore the extraneous.
	why are we doing spiral?  why not unittest freestyle first?
	arena size and gate are passed by args only in sim mode
	turning radius can be adjusted by machine learning and should be saved with the skate id

refactor ala sk8 sensoryMotorCircuit
	2 simultaneous tasks
		fly the drone
		drive the skate
	both require navigation and piloting
	navigator and pilot
	to navigate - plot a route, strategy
	to pilot - steer the vehicle along the route, tactics
	
	1st time
		if spec.live:
			use OpenCV to read frame from drone camera
			use TensorFlow to do object detection and segmentation of cones and skate
		elif spec.sim:
			generate arena, cones, skate
		use matplotlib to build map and plot route
	subsequent times:
		orient new map to master map
	
	while running:
		if spec.live:
			use OpenCV to read frame from drone camera
			use TensorFlow to do object detection and segmentation of cones and skate
		elif spec.sim:
			plot new position via dead reckoning
	
		set gate = skate starting position
		use matplotlib to plan route: calculate heading, bearings, route
		use matplotlib to navigate: calculate heading, bearings
		use matplotlib to pilot: calculate helm, speed
		use matplotlib to draw map
		use OpenCV.addWeighted to overlay map on top of camera image
		use OpenCV to show the finished photo
		use OpenCV.waitKey(0) to allow user override

refactor ala args.py
	x fix argument passing of:
		x arena_spec
		x event_spec
		x skate_spec
		x run_spec
	x rename:
		x %s/arena_spec\['w'\]/spec.arenawidth/gc
		x %s/arena_spec\['h'\]/spec.arenaheight/gc
		x %s/arena_spec\['gate'\]/(spec.gatex,spec.gatey)/gc
	        x %s/arena_spec\['conecolor'\]/spec.conecolor/gc
	        x %s/arena_spec\['routecolor'\]/spec.routecolor/gc
		x %s/run_spec\['quiet'\]/spec.quiet/gc
		x %s/run_spec\['simmode'\]/spec.simmode/gc
		x %s/skate_spec\['drift'\]/spec.drift/gc
		x %s/args.output/spec.output/gc
		x %s/run_spec\['trail'\]/spec.trail/gc
		x %s/run_spec\['fps'\]/spec.fps/gc
		x %s/run_spec\['startdelay'\]/spec.startdelay/gc
		x %s/args.testdata/spec.suite/gc
		- %s/event_spec\['event'\]/spec.event/gc
		x %s/event_spec\['num_cones'\]/spec.numcones/gc
		x %s/skate_spec\['turning_radius'\]/spec.turningradius/gc
		x %s/skate_spec\['length'\]/spec.skatelength/gc
		- %s/skate_spec\['width'\]/spec.skatewidth/gc
		- %s/skate_spec\['color'\]/spec.skatecolor/gc
		x %s/skate_spec\['avgspeed'\]/spec.avgspeed/gc
		- %s/skate_spec\['helmlag'\]/spec.helmlag/gc
		x %s/skate_spec\['helmpct'\]/spec.helmpct/gc
		x %s/skate_spec\['helmrange'\]/spec.helmrange/gc
        

'''

