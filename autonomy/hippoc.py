'''hippoc.py
skateboard cones
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

for each cone
cente
entry point
exit point


for each cone
	center
	entry: slope, perp, thetaC, thetaD, choice
	exit:  slope, perp, thetaC, thetaD, choice
	theta_entry	
	theta_exit

make entry choice
	if angle between line in and line out > 90 degrees?

make exit choice
	go around the cone once?

polar coordinates (range, bearing) to cartesian coordinates (x,y)
http://rossum.sourceforge.net/papers/CalculationsForRobotics/CirclePath.htm


enter on the left, go clockwise
enter on the right, go counter-clockwise
'''

import numpy as np
import matplotlib.pyplot as plt  
import matplotlib  
import mpmath  
import math

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

def calcPerpendicular(A,B,radius):
	# see https://stackoverflow.com/questions/57065080/draw-perpendicular-line-of-fixed-length-at-a-point-of-another-line

	# calc slope of A to B
	slope = (B[1] - A[1]) / (B[0] - A[0]) # slope of AB, rise over run
	l2r = (B[0] - A[0]) > 0  # horse is running left to right, true or false
	lo2hi = (B[1] - A[1]) > 0  # horse is running low to high, true or false

	# B = next or current point
	# A = previous point

	# A = previous cone
	# B = current cone
	# next cone

	r = {
		'pointC': [0,0],
		'thetaC': [0,0],
		'pointD': 0,
		'thetaD': 0, 
		'θC': 0,
		'θD': 0,
	}

	# slope of CD as dy/dx
	dy = math.sqrt(radius**2/(slope**2+1))
	dx = -slope*dy
	diff = [dx, dy]

	# calc xy endpoints CD of perpendicular across the circle at B
	if l2r:
		C = B + diff
		D = B - diff
	else:
		C = B - diff
		D = B + diff

	if lo2hi:
		thetaD = math.degrees(np.arctan(dy/dx))
		thetaC = thetaD + 180
	else:
		thetaC = math.degrees(np.arctan(dy/dx))
		thetaD = thetaC + 180


	return {
		'center': B,
		'slope': slope,
		'l2r': l2r,
		'perp': [C,D],
		'thetaC': thetaC,
		'thetaD': thetaD,
		'enterleft': np.random.choice([True, False])
	}
		

def calcRoute(cones, skate):
	
	xcones = []
	for i in range(1,cones.shape[0]-1):
		# entry point
		A = cones[i-1]  # previous point
		B = cones[i]    # this point
		entry = calcPerpendicular(A,B,skate['turning_radius'])
		#x,y = np.transpose(entry['perp'])
		#plt.plot(x,y)
	
		# exit point
		A = cones[i+1]  # next point
		B = cones[i]    # this point
		exit = calcPerpendicular(A,B,skate['turning_radius'])
		#x,y = np.transpose(exit['perp'])
		#plt.plot(x,y)
	
		xcones.append({'center':cones[i], 'entry':entry, 'exit':exit})

	return xcones
	
# setup the arena
cones = placeConesInArena(arena_spec, num_cones)

# draw center points
x,y = np.transpose(cones); 
plt.scatter(x,y)
print(cones)

# draw a circle around each center point
#radius = skate_spec['turning_radius']
#for pt in cones:
#	c = plt.Circle(pt, radius, fill=False)
#	plt.gca().add_patch(c)

# draw lines connecting center points
#x,y = np.transpose(cones)
#plt.plot(x,y)

# plot course
route = calcRoute(cones, skate_spec)
#print(route)

for e in route:
	print(e['entry']['thetaC'], e['entry']['thetaD'])


# draw an arc from entry to exit
radius = skate_spec['turning_radius']
for pt in route:
	print(pt['entry']['enterleft'])
	if pt['entry']['enterleft']:  #CW D to C
		a = matplotlib.patches.Arc(pt['center'], radius*2, radius*2, 0, pt['exit']['thetaD'], pt['entry']['thetaC'], color='blue')
		plt.gca().add_patch(a)
	else:  #CCW C to D
		a = matplotlib.patches.Arc(pt['center'], radius*2, radius*2, 0, pt['entry']['thetaD'], pt['exit']['thetaC'], color='red')
		plt.gca().add_patch(a)

# draw entry and exit points
entrypoints = []
exitpoints = []
for pt in route:
	#entrypoints.append(pt['entry']['perp'][0])
	#exitpoints.append(pt['exit']['perp'][1])
	entrypoints.append(pt['entry']['perp'][1])
	exitpoints.append(pt['exit']['perp'][0])
x,y = np.transpose(entrypoints); 
plt.scatter(x,y,color='green')
x,y = np.transpose(exitpoints); 
plt.scatter(x,y,color='red')

def plotline(line):
	x,y = np.transpose(line)
	plt.plot(x,y, color='black', lw=1)

# draw lines from cone to cone, exit to entry
plotline([cones[0], route[0]['entry']['perp'][1]]) # starting gate
for i in range(1,len(route)):
	pt = route[i]
	if pt['entry']['enterleft']:
		entrypoint = route[i]['entry']['perp'][0]
	else:
		entrypoint = pt['entry']['perp'][1]

	#plotline([route[i-1]['exit']['perp'][1], route[i]['entry']['perp'][0]])
	plotline([route[i-1]['exit']['perp'][0], route[i]['entry']['perp'][1]])
plotline([route[len(route)-1]['exit']['perp'][0], cones[0]]) # back to starting gate

# draw arena
plt.xlim(0,arena_spec['w'])
plt.ylim(0,arena_spec['h'])
plt.autoscale(False)
plt.gca().set_aspect('equal', anchor='C')
plt.show()

