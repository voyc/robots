'''hippoc.py

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

isTest = True 
testLeft = True

arena_spec = {
	'w':4000,
	'h': 4000,
	'title': 'Arena',
	'gate': [2000,50],
}

event_spec = {
	'event': 'freestyle',
	'num_cones': 5,
}

skate_spec = {
	'turning_radius': 200,
}

def placeCones(arena, num_cones):
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
	pool = pool[:num_cones]

	# center the cones in the arena
	tpool = np.transpose(pool)
	lo = np.array([tpool[0].min(), tpool[1].min()])
	hi = np.array([tpool[0].max(), tpool[1].max()]) 
	bbox_center = lo + ((hi - lo) / 2)
	arena_center = np.array([int(arena['w']/2), int(arena['h']/2)])
	adj = arena_center - bbox_center
	pool = np.add(pool,adj)
	
	# test case
	if isTest:
		pool = 	[[1704.5,  667. ], 
			 [3588.5, 1410. ], # +slope, +dy, +dx, up  , to the right, quadrant 1
			 [1294.5, 3333. ], # -slope, +dy, -dx, up  , to the left , quadrant 2
			 [2928.5, 2561. ], # -slope, -dy, +dx, down, to the right, quadrant 4
			 [ 411.5,  787. ]] # +slope, -dy, -dx, down, to the left , quadrant 3
	return pool
		
def planRoute(cones):
	# not implemented yet
	# return an extended version of the cones array with enterleft choices
	xcones = []
	for i in range(cones.shape[0]-1):
		choice = np.random.choice([True,False])
		xcones.append({
			'center':cones[i], 
			'enterleft': np.random.choice([True,False])
		})
	return xcones
	

def planRoute(cones, skate):
	# return an extended version of the cones array with calculations
	xcones = []

	# add starting and ending gate to temp copy of cones array
	gate = arena_spec['gate']
	cones = np.insert(cones,0,[gate],axis=0)
	cones = np.append(cones,[gate],axis=0)

	for i in range(1,cones.shape[0]-1):
		# entry point
		A = cones[i-1]  # previous point
		B = cones[i]    # this point
		L, R, thetaL, thetaR,_,_ = nav.calcPerpendicular(A, B, skate['turning_radius'])
		entry = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		# exit point
		A = cones[i+1]  # next point
		B = cones[i]    # this point
		L, R, thetaL, thetaR,_,_ = nav.calcPerpendicular(A,B,skate['turning_radius'])
		exit = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		# make choice: left or right entry
		enterleft = np.random.choice([True,False])
		if isTest: enterleft = testLeft

		xcones.append({
			'center':cones[i], 
			'entry':entry, 
			'exit':exit, 
			'enterleft': enterleft
		})

	return xcones
	
# setup arena
cones = placeCones(arena_spec, event_spec['num_cones'])

# draw arena
print(cones)
radius = skate_spec['turning_radius']
i = 0
for pt in cones:
	plt.text( pt[0], pt[1], str(i+1), fontsize='14', ha='center', va='center', color='cyan')
	#c = plt.Circle(pt, radius, fill=False); plt.gca().add_patch(c)
	i += 1
x,y = np.transpose(arena_spec['gate']); plt.scatter(x,y, color='cyan')

# plot route
route = planRoute(cones, skate_spec)
#route = plotRoute(route, skate_spec)

# draw route
for r in route: print(r['center'])

def drawline(line, color='black'): x,y = np.transpose(line); plt.plot(x,y, color=color, lw=1)
def drawpoint(pt,color='black'): x,y = np.transpose(pt); plt.scatter(x,y,color=color)

#prevexitpoint = arena_spec['gate']
#for i in range(0,len(route)):
#	pt = route[i]
#
#	#print(pt['enterleft'])
#	if pt['enterleft']:  # CW L to R (Arc always goes CCW)
#		theta1 = pt['exit']['thetaR'] 
#		theta2 = pt['entry']['thetaL']
#		entrypoint = pt['entry']['L']
#		exitpoint = pt['exit']['R']
#	else:  # CCW R to L
#		theta1 = pt['entry']['thetaR']
#		theta2 = pt['exit']['thetaL']
#		entrypoint = pt['entry']['R']
#		exitpoint = pt['exit']['L']
#
#	#drawline([pt['entry']['R'], pt['entry']['L']], 'green')
#	#drawline([pt['exit']['R'], pt['exit']['L']], 'red')
#	#drawpoint(entrypoint, color='green')
#	#drawpoint(exitpoint, color='red')
#
#	a = matplotlib.patches.Arc(pt['center'], radius*2, radius*2, 0, math.degrees(theta1), math.degrees(theta2), color='black')
#	plt.gca().add_patch(a)
#
#	drawline([prevexitpoint, entrypoint])
#	prevexitpoint = exitpoint
#
#drawline([prevexitpoint, arena_spec['gate']])

# save route
xroute = []
prevexitpoint = arena_spec['gate']
for i in range(0,len(route)):
	pt = route[i]

	#print(pt['enterleft'])
	if pt['enterleft']:  # CW L to R (Arc always goes CCW)
		theta1 = pt['exit']['thetaR'] 
		theta2 = pt['entry']['thetaL']
		entrypoint = pt['entry']['L']
		exitpoint = pt['exit']['R']
	else:  # CCW R to L
		theta1 = pt['entry']['thetaR']
		theta2 = pt['exit']['thetaL']
		entrypoint = pt['entry']['R']
		exitpoint = pt['exit']['L']

	#drawline([pt['entry']['R'], pt['entry']['L']], 'green')
	#drawline([pt['exit']['R'], pt['exit']['L']], 'red')
	#drawpoint(entrypoint, color='green')
	#drawpoint(exitpoint, color='red')

	heading = nav.calcHeading(prevexitpoint, entrypoint)

	xroute.append({
		'type': 'line',
		'from': prevexitpoint,
		'to': entrypoint,
		'heading': heading,
	})

	xroute.append({
		'type': 'arc',
		'from': theta1,
		'to': theta2,
		'wise': 'cw',
	})

	a = matplotlib.patches.Arc(pt['center'], radius*2, radius*2, 0, math.degrees(theta1), math.degrees(theta2), color='black')
	plt.gca().add_patch(a)

	drawline([prevexitpoint, entrypoint])
	prevexitpoint = exitpoint



drawline([prevexitpoint, arena_spec['gate']])
xroute.append({
	'type': 'line',
	'from': prevexitpoint,
	'to': entrypoint,
	'heading': heading,
})

for pt in xroute: print(pt)

# initializing a line variable
line, = plt.gca().plot([], [], lw = 3) 
begin = 0
end = 200
girth = 20
speed = 15
   

def init(): # called once before first frame
	
	x,y = np.transpose([xroute[0]['from'], xroute[0]['to']])
	plt.plot(x,y, color='blue', lw=5)
	line.set_data(x, y)
	return line,
   
def animate(frame): # called once for every frame
	global line, begin, end, girth
	x = np.linspace(begin, end, girth)

	y = x * 2
	line.set_data(x, y)
  
	begin += speed
	end += speed
	return line, # because blit=True, return a list of artists

fig = plt.gcf()
   
anim = FuncAnimation(fig, animate, init_func=init, frames=range(1,200), interval=20, blit=True)
  
# draw arena
plt.xlim(0,arena_spec['w'])
plt.ylim(0,arena_spec['h'])
plt.autoscale(False)
plt.gca().set_aspect('equal', anchor='C')
plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
plt.gca().spines['bottom'].set_color('cyan')
plt.gca().spines['top'].set_color('cyan')
plt.gca().spines['left'].set_color('cyan')
plt.gca().spines['right'].set_color('cyan')
plt.show()
