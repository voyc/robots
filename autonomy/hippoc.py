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
'''

import numpy as np
import matplotlib.pyplot as plt  
import matplotlib  
import mpmath  
import math
import perp

arena_spec = {
	'w':4000,
	'h': 4000,
	'title': 'Arena'
}

num_cones = 5

skate_spec = {
	'turning_radius': 200,
}

def placeConesInArena(arena, num_cones):
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
	if False:
		pool = 	[[1704.5,  667. ],
			 [3588.5, 1410. ],
			 [1294.5, 3333. ],
			 [2928.5, 2561. ],
			 [ 411.5,  787. ]]

	# add starting gate
	gate = [int(arena['w']/2),10]
	pool = np.insert(pool,0,[gate],axis=0)
	pool = np.append(pool,[gate],axis=0)
	return pool

def calcRoute(cones, skate):
	
	xcones = []
	for i in range(1,cones.shape[0]-1):
		# entry point
		A = cones[i-1]  # previous point
		B = cones[i]    # this point
		L, R, thetaL, thetaR,_,_ = perp.calcPerpendicular(A, B, skate['turning_radius'])
		entry = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		# exit point
		A = cones[i+1]  # next point
		B = cones[i]    # this point
		L, R, thetaL, thetaR,_,_ = perp.calcPerpendicular(A,B,skate['turning_radius'])
		exit = {
			'L': L,
			'R': R,
			'thetaL': thetaL,
			'thetaR': thetaR
		}
	
		xcones.append({
			'center':cones[i], 
			'entry':entry, 
			'exit':exit, 
			'enterleft': np.random.choice([True,False])
		})

	return xcones
	
# setup arena
cones = placeConesInArena(arena_spec, num_cones)

# draw arena
print(cones)
radius = skate_spec['turning_radius']
i = 0
for pt in cones:
	if i == 0 or i == len(cones)-1:
		x,y = np.transpose(pt); plt.scatter(x,y, color='cyan')
	else:
		plt.text( pt[0], pt[1], str(i), fontsize='14', ha='center', va='center', color='cyan')
	#c = plt.Circle(pt, radius, fill=False); plt.gca().add_patch(c)
	i += 1

# plot route
route = calcRoute(cones, skate_spec)

# draw route
#print(route)

def drawline(line, color='black'): x,y = np.transpose(line); plt.plot(x,y, color=color, lw=1)
def drawpoint(pt,color='black'): x,y = np.transpose(pt); plt.scatter(x,y,color=color)

prevexitpoint = cones[0]  # starting gate
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

	a = matplotlib.patches.Arc(pt['center'], radius*2, radius*2, 0, math.degrees(theta1), math.degrees(theta2), color='black')
	plt.gca().add_patch(a)

	drawline([prevexitpoint, entrypoint])
	prevexitpoint = exitpoint

drawline([prevexitpoint, cones[0]]) # back to starting gate

# draw arena
plt.xlim(0,arena_spec['w'])
plt.ylim(0,arena_spec['h'])
plt.autoscale(False)
plt.gca().set_aspect('equal', anchor='C')
plt.show()

