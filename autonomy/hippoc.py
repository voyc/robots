'''hippoc.py
Freestyle barrel racing.
The aesthetic control available:
- choose order of barrels
- choose direction around each barrel, cw or ccw

One brain part executing.  Tactics.
One brain part planning future.  Strategy.
Aesthetics can be found in both: strategy and tactics.

'''
import numpy as np
import matplotlib.pyplot as plt  
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

def placeConesInArena(spec, num_cones):
	#constants
	min_dist_factor = 0.3
	starting_pool_size = 100
	margin_factor = 0.05

	#calculations
	margin = int(((spec['w'] + spec['h']) / 2) * margin_factor)
	min_dist = int(((spec['w'] + spec['h']) / 2) * min_dist_factor)
	
	# get a pool of points
	x = np.random.randint(low=margin, high=spec['w']-margin, size=(starting_pool_size,1), dtype=int)
	y = np.random.randint(low=margin, high=spec['h']-margin, size=(starting_pool_size,1), dtype=int)
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
	arena_center = np.array([int(spec['w']/2), int(spec['h']/2)])
	adj = arena_center - bbox_center
	pool = np.add(pool,adj)

	# add starting gate
	gate = [int(spec['w']/2),10]
	pool = np.insert(pool,0,[gate],axis=0)
	pool = np.append(pool,[gate],axis=0)
	
	return pool

def calcRoute(skate):
	# draw perpendicular
	# see https://stackoverflow.com/questions/57065080/draw-perpendicular-line-of-fixed-length-at-a-point-of-another-line
	
	# draw a circle around each point
	for pt in cones:
		c = plt.Circle(pt, skate['turning_radius'], fill=False)
		plt.gca().add_patch(c)
		
	route = np.copy(cones)
	for i in range(1,cones.shape[0]-1):
		A = cones[i-1]
		B = cones[i]
		C = [0,0]
		D = [0,0]
		slope = (B[1] - A[1]) / (B[0] - A[0])
		dy = math.sqrt(skate['turning_radius']**2/(slope**2+1))
		dx = -slope*dy
		C[0] = B[0] + dx
		C[1] = B[1] + dy
		D[0] = B[0] - dx
		D[1] = B[1] - dy
	
		line = [C,D]
		x,y = np.transpose(line)
		plt.plot(x,y)
	
		# draw tangents
		side = np.random.choice(['right', 'left'])
		if side == 'right':
			tangent = C
		else:
			tangent = D
		route[i,0] = tangent[0]
		route[i,1] = tangent[1]
	
		# draw reverse tangent
		A = cones[i]
		B = cones[i-1]
		C = [0,0]
		D = [0,0]
		slope = (B[1] - A[1]) / (B[0] - A[0])
		dy = math.sqrt(skate['turning_radius']**2/(slope**2+1))
		dx = -slope*dy
		C[0] = B[0] + dx
		C[1] = B[1] + dy
		D[0] = B[0] - dx
		D[1] = B[1] - dy
	
		line = [C,D]
		x,y = np.transpose(line)
		plt.plot(x,y)
	
		# draw tangents
		side = np.random.choice(['right', 'left'])
		if side == 'right':
			tangent = C
		else:
			tangent = D
		route = np.insert(route,i,tangent,axis=0)
		#route[i,0] = tangent[0]
		#route[i,1] = tangent[1]
	
	
	x,y = np.transpose(route)
	plt.plot(x,y)
	
	
	'''
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
	
	'''
	
	return	

# setup the arena
cones = placeConesInArena(arena_spec, num_cones)
x,y = np.transpose(cones); 
plt.scatter(x,y)

# plot course
route = calcRoute(skate_spec)

# draw arena
plt.xlim(0,arena_spec['w'])
plt.ylim(0,arena_spec['h'])
plt.autoscale(False)
plt.gca().set_aspect('equal', anchor='C')
plt.show()

