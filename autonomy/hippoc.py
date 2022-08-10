'''hippoc.py
Freestyle barrel racing.
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
center
entry point
exit point


for each cone
	center
	entry: slope, lineseg, theta1, theta2, choice
	exit:  slope, lineseg, theta1, theta2, choice
	theta_entry	
	theta_exit

make entry choice
	if angle between line in and line out > 90 degrees?

make exit choice
	go around the cone once?

'''

import numpy as np
import matplotlib.pyplot as plt  
import matplotlib  
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

	# add starting gate
	gate = [int(arena['w']/2),10]
	pool = np.insert(pool,0,[gate],axis=0)
	pool = np.append(pool,[gate],axis=0)
	
	return pool

def calcPerpendicular(A,B,radius):
	# see https://stackoverflow.com/questions/57065080/draw-perpendicular-line-of-fixed-length-at-a-point-of-another-line

	# calc slope of A to B
	slope = (B[1] - A[1]) / (B[0] - A[0]) # slope of AB, rise over run

	# slope of CD as dy/dx
	dy = math.sqrt(radius**2/(slope**2+1))
	dx = -slope*dy
	diff = [dx, dy]
	print(slope,dx,dy)

	# calc xy endpoints CD of perpendicular across the circle
	C = [0,0]
	D = [0,0]
	C[0] = B[0] + dx
	C[1] = B[1] + dy
	D[0] = B[0] - dx
	D[1] = B[1] - dy
	return [C,D]

def calcRoute(cones, skate):
	
	xcones = np.array([[cones[0], cones[0], cones[0]]]) # starting gate
	for i in range(1,cones.shape[0]-1):
		# entry point
		A = cones[i-1]  # previous point
		B = cones[i]    # this point
		perp = calcPerpendicular(A,B,skate['turning_radius'])
		entry = perp[0] if np.random.choice(['r', 'l']) == 'r' else perp[1]
		x,y = np.transpose(perp)
		plt.plot(x,y)
	
		# exit point
		A = cones[i+1]  # next point
		B = cones[i]    # this point
		perp = calcPerpendicular(A,B,skate['turning_radius'])
		exit = perp[0] if np.random.choice(['r', 'l']) == 'r' else perp[1]
		x,y = np.transpose(perp)
		plt.plot(x,y)
	
		xcones = np.insert(xcones,i, np.array([cones[i], entry, exit]), axis=0)

	xcones = np.insert(xcones,i+1, xcones[0], axis=0) # back to starting gate
	return xcones
	
# setup the arena
cones = placeConesInArena(arena_spec, num_cones)

# draw center points
#x,y = np.transpose(cones); 
#plt.scatter(x,y)

# draw a circle around each center point
radius = skate_spec['turning_radius']
for pt in cones:
	c = plt.Circle(pt, radius, fill=False)

	a = matplotlib.patches.Arc(pt, radius*2, radius*2, 0, 90, 270)

	plt.gca().add_patch(a)




# draw lines connecting center points
x,y = np.transpose(cones)
plt.plot(x,y)

# plot course
route = calcRoute(cones, skate_spec)

print(cones)
print(route)

# draw entry and exit points points
x,y = np.transpose(route); 
plt.scatter(x[1],y[1],color='green')
plt.scatter(x[2],y[2],color='red')

# draw lines from exit to entry
#x,y = np.transpose(route)
#plt.plot(x,y)

# draw arena
plt.xlim(0,arena_spec['w'])
plt.ylim(0,arena_spec['h'])
plt.autoscale(False)
plt.gca().set_aspect('equal', anchor='C')
plt.show()

