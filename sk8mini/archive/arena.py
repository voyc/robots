'''
arena.py - implement class Arena

	mark rounding:
		go-around
		cloverleaf
		touch-and-go : prev mark, next mark
	barrel-race vs slalom

'''

import random
import specs
import nav

class Mark:
	conendx = 0
	rdir = 'cw'
	center = [0,0]   # copy of cones[conendx]
	entry = [0,0]
	exit = [0,0]
	def __str__(self):
		return f'{self.conendx}, {self.rdir}, {self.center}, {self.entry}, {self.exit}'

	def __init__(self, ndx, rdir, ctr):
		self.conendx = ndx
		self.rdir = rdir
		self.center = ctr

	@classmethod
	def fromGate(self, gate):
		self.conendx = -1
		self.rdir = -1
		self.center = gate
		return self

class Arena:
	gate = [0,0]
	cones = []
	numcones = len(cones)
	marks = []
	waypts = []
	#plan = []      # plan, route, leg - replaced with marks and waypts
	#route = []	# list of legs
	#routendx = 0	# current index into the route list
	#leg = {}	# current leg
	on_mark_distance = 8
	steady_helm_distance = 12

	def firstCone(self, pos, heading):
		def shortestAngleBetweenTwoHeadings(a,b): # cw or ccw
			angle1 = ((a - b) + 360) % 360
			angle2 = ((b - a) + 360) % 360
			return min(angle1,angle2)

		errs = []
		for i in range(len(self.cones)):
			cone = self.cones[i]
			bearing = nav.headingOfLine(pos, cone)
			err = shortestAngleBetweenTwoHeadings(bearing, heading)
			errs.append([err, i])
		ndx = sorted(errs)[0][1]
		return ndx

	
	def addPattern(self, pattern, numcones, rdir, reps):
		global photo
		print(sensor)
		print(photo)
		print(pattern, numcones, rdir, reps)
	
		# ------------------
		# create a list of cone-index numbers, with a given count and order
		conendxs = None
		if type(numcones) is list:
			conendxs = numcones # caller has specified the list explicitly
		else:
			if numcones == 0:
				if pattern == 'spin': numcones = 1
				elif pattern == 'oval': numcones = 2
				elif pattern == 'figure-8': numcones = 2
				elif pattern == 'barrel-race' : numcones = 3
				else: numcones = random.randrange(1, self.numcones)
		
			allconendxs = [i for i in range(len(self.cones))]  # population
			conendxs = random.sample(allconendxs,  numcones)    # sample
		
			if len(self.marks) == 0:  # first-time
				firstcone = self.firstCone(photo.cbase, sensor.heading)
				if firstcone in conendxs:
					conendxs.pop(conendxs.index(firstcone))
				else:
					conendxs.pop()
				conendxs.insert(0,firstcone)
			else:
				lastcone = self.marks[len(self.marks)-1].conendx
				if conendxs[0] == lastcone:
					conendxs.pop(0)
					conendxs.append(lastcone)

		print(conendxs, len(conendxs))
	
		# --------------------------
		# create a list of rotational-directions, one for each cone-index
		# input rdir can be 0, 'alt', 'cw', or 'ccw'
		def alt(rdir): return 'cw' if rdir == 'ccw' else 'ccw'
		rdirs = []
		i = 0
		for ndx in conendxs:
			thisrdir = None
			if rdir in ['cw','ccw']: thisrdir = rdir  
			else: thisrdir = random.choice(['cw','ccw'])
	
			if i>0:
				if pattern in ['figure-8','slalom'] or rdir == 'alt':
					thisrdir = alt(rdir[i-1])
				elif pattern in ['oval','perimeter']:
					thisrdir = rdirs[0]
	
			rdirs.append(thisrdir)
			i += 1
		print(rdirs, len(rdirs))
	
		# --------------------------
		# create a list of marks for this pattern, and add it to master mark list
		if reps == 0: reps = random.randrange(0,5)
		marks = []
		for i in range(reps):
			for j in range(len(conendxs)):
				mark = Mark(conendxs[j], rdirs[j], self.cones[conendxs[j]])
				marks.append(mark)
		self.marks += marks # add this pattern to the master

		# --------------------------
		# add entry and exit points to each mark
		r = specs.turning_radius
		gatemark = Mark.fromGate(self.gate)

		for i in range(len(self.marks)):
			mark = self.marks[i]
			prevmark = gatemark if i <= 0 else self.marks[i-1]
			nextmark = gatemark if i+1 >= len(self.marks) else self.marks[i+1] 
	
			# entry point
			A = prevmark.center
			B = mark.center
			L, R = nav.linePerpendicular(A, B, r)
			entry = {
				'L': L,
				'R': R,
			}
		
			# exit point
			A = nextmark.center
			B = mark.center
			L, R = nav.linePerpendicular(A,B,r)
			exit = {
				'L': L,
				'R': R,
			}
		
			if mark.rdir == 'cw':
				mark.entry = entry['L']
				mark.exit  = exit['R']
			else:
				mark.entry = entry['R']
				mark.exit  = exit['L']

		# --------------------------
		# create a list of waypointss for this pattern, and add it to master waypoint list
		if len(self.waypts) <= 0:  # first-time
			self.waypts.append( gatemark.center)  # starting gate
			self.waypts.append( gatemark.center)  # finish gate

		waypts = []
		for i in range(len(marks)):
			mark = marks[i]
			waypts.append( mark.entry)
			waypts.append( mark.exit)

		# insert these waypoints into the master list, just before the finish gate
		gate = self.waypts.pop()
		self.waypts += waypts
		self.waypts.append(gate)

def printlist(olist): 
	for o in olist: print(o)

def main():
	global sensor, photo
	class Sensor:
		heading = 10
	class Photo:
		cbase = [10,10]
	sensor = Sensor()
	photo = Photo()

	arena = Arena()
	arena.gate = [-120,-120]
	arena.cones = specs.vcones['iron-cross']
	arena.numcones = len(arena.cones)

	arena.addPattern( 0, 0, 0, 0)
	#arena.addPattern( 'oval', 2, 'cw', 3)
	#arena.addPattern( 'oval', 2, 'ccw', 3)
	#arena.addPattern( 'oval', 2, 0, 3)
	#arena.addPattern( 'figure-8', 2, 'alt', 3)
	#arena.addPattern( 'barrel-race', 3, '', 3)
	#arena.addPattern( 'random', 0, 0, 3)
	#arena.addPattern( 'oval', [1,2], 'cw', 3)
	#arena.addPattern( 'spin', [3], 'cw', 3)

	print()
	printlist(arena.marks)
	print(len(arena.marks))

	print()
	printlist(arena.waypts)
	print(len(arena.waypts))

if __name__ == '__main__':
	main()

