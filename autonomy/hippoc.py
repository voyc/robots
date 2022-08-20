''' hippoc.py

skateboard cones

three events:
	barrel racing
	slalom https://www.youtube.com/watch?v=sYSr-Sft4Zk
	freestyle

The aesthetic control available:
- choose order of barrels
- choose direction around each barrel, cw or ccw

One brain part executing.  Tactics.
One brain part planning future.  Strategy.
Aesthetics can be found in both: strategy and tactics.

arena of 5 cones
strategy - 
  next three barrels: choose barrel and side
  draw route
tactics - ? 
  for a given speed, move ahead n pixels
  am i on the line
  adjust to get back to the line

stay between the lines
stay on the line
aim at a spot
constantly self correct

enter on the left, go clockwise around the cone
enter on the right, go counter-clockwise

calculations and drawing should be separate
calc, draw, navigate

todo
- collision avoidance 
	- run through one cone on the way to another
	- pass by with slight bend
	- circle, go clear around before continuing same direction
- implement barrel racing
- implement slalom
- implement incremental routing, three ahead
- implement animation, skate following path
- save plot into cv image ?
'''

import numpy as np
import matplotlib.pyplot as plt  
import matplotlib  
import mpmath  
import math
import nav
from matplotlib.animation import FuncAnimation 
import copy

isTest = True 
test1 =	[{'center':[1704.5,  667. ], 'enterleft':True }, 
	 {'center':[3588.5, 1410. ], 'enterleft':True }, # +slope, +dy, +dx, up  , to the right, quadrant 1
	 {'center':[1294.5, 3333. ], 'enterleft':True }, # -slope, +dy, -dx, up  , to the left , quadrant 2
	 {'center':[2928.5, 2561. ], 'enterleft':True }, # -slope, -dy, +dx, down, to the right, quadrant 4
	 {'center':[ 411.5,  787. ], 'enterleft':True }] # +slope, -dy, -dx, down, to the left , quadrant 3

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
	'avgspeed': 15, # kmh
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
	# add enterleft choice to each cone
	for cone in cones:
		enterleft = np.random.choice([True,False])
		cone['enterleft'] = enterleft
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
		L, R, thetaL, thetaR,_,_ = nav.calcPerpendicular(A, B, r)
		entry = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		# exit point
		A = nextcone['center']
		B = cone['center']
		L, R, thetaL, thetaR,_,_ = nav.calcPerpendicular(A,B,r)
		exit = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		cone['entry'] = entry
		cone['exit'] = exit
	return cones
	
def buildRoute(cones, skate):
	route = []
	gate = arena_spec['gate']
	prevexitpoint = gate
	for i in range(0,len(cones)):
		cone = cones[i]
	
		if cone['enterleft']:  # CW L to R (Arc always goes CCW)
			theta1 = cone['exit']['thetaR'] 
			theta2 = cone['entry']['thetaL']
			entrypoint = cone['entry']['L']
			exitpoint = cone['exit']['R']
		else:  # CCW R to L
			theta1 = cone['entry']['thetaR']
			theta2 = cone['exit']['thetaL']
			entrypoint = cone['entry']['R']
			exitpoint = cone['exit']['L']
	
		heading = nav.lineHeading(prevexitpoint, entrypoint)
	
		route.append({
			'shape': 'line',
			'from': prevexitpoint,
			'to': entrypoint,
			'heading': heading,
		})
	
		route.append({
			'shape': 'arc',
			'from': theta1,
			'to': theta2,
			'center': cone['center'],
		})
		
		prevexitpoint = exitpoint
	
	# back to starting gate
	heading = nav.lineHeading(prevexitpoint, gate)
	route.append({
		'shape': 'line',
		'from': prevexitpoint,
		'to': gate,
		'heading': heading,
	})
	return route

def drawRoute(route, arena, skate):
	def drawLine(line, color='black'): 
		x,y = np.transpose(line); 
		plt.plot(x,y, color=color, lw=1)

	def drawPoint(pt, color='black'): 
		x,y = np.transpose(pt); 
		plt.scatter(x,y,color=color)

	def drawArc(pt, r, theta1, theta2, color='black'): 
		a = matplotlib.patches.Arc(pt, r*2, r*2, 0, math.degrees(theta1), math.degrees(theta2), color=color)
		plt.gca().add_patch(a)

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
			drawArc(leg['center'], radius, leg['from'], leg['to'], color)

def drawArena(cones, arena):
	# draw cones
	color = arena['conecolor'] 
	radius = skate_spec['turning_radius']
	i = 0
	for cone in cones:
		pt = cone['center']
		plt.text( pt[0], pt[1], str(i+1), fontsize='14', ha='center', va='center', color=color)
		#c = plt.Circle(pt, radius, fill=False); plt.gca().add_patch(c)
		i += 1

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

# a line2D artist object to represent the skate, used by FuncAnimation
color = skate_spec['color']
points_per_pixel = 7  # linewidth is given in "points"
lw = int(skate_spec['width'] / points_per_pixel)
skateline, = plt.gca().plot([], [], lw=lw, color=color)

# animation variables
speed = kmh2cps(skate_spec['avgspeed'])
lastKnownPosition = arena_spec['gate']
lastKnownHeading = 0 # compass heading
lastKnownSteeringAngle = 0 # relative bearing

# animation constants
delay = int(1000 / animation_spec['fps']) # delay between frames in milliseconds


def drawSkate(): # based on position and heading
	global lastKnownPosition, lastKnownHeading
	bow,stern = nav.calcLineWithHeading(lastKnownPosition, lastKnownHeading, skate_spec['length'])
	x,y = np.transpose([stern, bow])
	return x,y

def positionSkate(prevPos, framenum):
	x,y = np.transpose(prevPos)
	y += framenum
	newPos = [x,y]
	return newPos

def init(): # called once before first frame, but in fact is called twice
	# set initial position of skateline
	global skateline
	x,y = drawSkate()
	skateline.set_data(x, y)
	return skateline,

def animate(framenum): # called once for every frame
	global skateline, lastKnownPosition
	lastKnownPosition = positionSkate(lastKnownPosition, framenum)
	x,y = drawSkate()
	skateline.set_data(x, y)
	return skateline, # because blit=True, return a list of artists

# main
cones = placeCones(arena_spec, event_spec)
cones = chooseSides(cones)
if isTest: cones = test1
cones = calcCones(cones, skate_spec)
route = buildRoute(cones, skate_spec)
drawArena(cones, arena_spec)
drawRoute(route, arena_spec, skate_spec)

anim = FuncAnimation(plt.gcf(), animate, init_func=init, frames=None, interval=delay, blit=True)
 
for cone in cones: print(cone['center'], cone['enterleft'])
for leg in route: print(leg)

plt.show()

