'''hippoc.py'''
import numpy as np
import matplotlib.pyplot as plt  
import math

title = 'Arena'

arena_x = 4000
arena_y = 4000
arena_margin_factor =.05
min_dist_factor =.3
turning_radius = 200
num_cones = 5
pool_size = 100

arena_margin = int(((arena_x + arena_y) / 2) * arena_margin_factor)
min_dist = int(((arena_x + arena_y) / 2) * min_dist_factor)

# get a pool of points
x = np.random.randint(low=arena_margin, high=arena_x-arena_margin, size=(pool_size,1), dtype=int)
y = np.random.randint(low=arena_margin, high=arena_y-arena_margin, size=(pool_size,1), dtype=int)
pool = np.transpose([x,y])[0]
#x,y = np.transpose(pool); plt.scatter(x,y)

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
#x,y = np.transpose(pool); plt.scatter(x,y)


# choose final four
pool = pool[:num_cones]
#x,y = np.transpose(pool); plt.scatter(x,y)

# calc bounding box
xlo = arena_x/2
xhi = xlo
ylo = arena_y/2
yhi = ylo
for pt in pool:
	if pt[0] > xhi:
		xhi = pt[0] 
	if pt[0] < xlo:
		xlo = pt[0] 
	if pt[1] > yhi:
		yhi = pt[1] 
	if pt[1] < ylo:
		ylo = pt[1] 

# draw the box
#print(xlo,xhi,ylo,yhi)
#plt.plot([xlo,xhi], [ylo,ylo])
#plt.plot([xlo,xhi], [yhi,yhi])
#plt.plot([xlo,xlo], [ylo,yhi])
#plt.plot([xhi,xhi], [ylo,yhi])

# find center of box
xc = xlo + int((xhi - xlo)/2)
yc = ylo + int((yhi - ylo)/2)

# find center of arena
xd = int(arena_x/2)
yd = int(arena_y/2)

# adjustment factor
xj = xd - xc
yj = yd - yc

# center the data
for pt in pool:
	pt[0] += xj
	pt[1] += yj

# draw the points
x,y = np.transpose(pool); plt.scatter(x,y)

# draw a circle around each point
for pt in pool:
	c = plt.Circle(pt, turning_radius, fill=False)
	plt.gca().add_patch(c)


# add starting gate
gate = [int(arena_x/2),10]
pool = np.insert(pool,0,[gate],axis=0)
pool = np.append(pool,[gate],axis=0)

# draw lines between all points
x,y = np.transpose(pool)
#plt.plot(x,y)

# draw perpendicular
# see https://stackoverflow.com/questions/57065080/draw-perpendicular-line-of-fixed-length-at-a-point-of-another-line
route = np.copy(pool)
for i in range(1,pool.shape[0]-1):
	print(i)
	A = pool[i-1]
	B = pool[i]
	C = [0,0]
	D = [0,0]
	slope = (B[1] - A[1]) / (B[0] - A[0])
	dy = math.sqrt(turning_radius**2/(slope**2+1))
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

x,y = np.transpose(route)
plt.plot(x,y)

route = np.copy(pool)
for i in reversed(range(1,pool.shape[0]-1)):
	print(i)
	A = pool[i]
	B = pool[i-1]
	C = [0,0]
	D = [0,0]
	slope = (B[1] - A[1]) / (B[0] - A[0])
	dy = math.sqrt(turning_radius**2/(slope**2+1))
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

x,y = np.transpose(route)
plt.plot(x,y)

#plt.plot([x[0],x[2]],[y[0],y[2]]) 
#plt.plot([x[0],x[3]],[y[0],y[3]]) 
#plt.plot([x[0],x[4]],[y[0],y[4]]) 

#plt.plot([x[1],x[2]],[y[1],y[2]]) 
#plt.plot([x[1],x[3]],[y[1],y[3]]) 
#plt.plot([x[1],x[4]],[y[1],y[4]]) 

#plt.plot([x[2],x[3]],[y[2],y[3]]) 
#plt.plot([x[2],x[4]],[y[2],y[4]]) 

#plt.plot([x[3],x[4]],[y[3],y[4]]) 


plt.xlim(0,arena_x)
plt.ylim(0,arena_y)
plt.autoscale(False)
plt.gca().set_aspect('equal', anchor='C')
plt.show()

