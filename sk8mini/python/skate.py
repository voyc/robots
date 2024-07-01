'''
skate.py - skate library imported by gcs.py

runs in the skate_process, launched by gcs.py 
communicates with sk8.ino

functions:
	on startup, calibrate the BRO055 sensor
	receive AHRS Sensor data sk8 via serial port dongle running gcs.ino
	receive donut center from awacs
	calculate wheelbase center by combining donut center, helm angle, roll angle
	navigate
	pilot
	send pilot commands to sk8 through the serial port dongle

Sensor can be called:
	AHRS - Attitude and Heading Reference System
	IMU - Inertial Measurement Unit

calibration:
	the BRO055 does three calibrations at random times in the background: 
		1. gyro calibration, easy, just let it sit still for a few seconds
		2. mag calibration, hard, move in a figure eight pattern repeatedly
		3. accel calibration, harder, we dont evey try

organization:  by roles, or brain parts:
	roles:
		captain - design route from choice of patterns 
		navigator - dead reckon position, adjust course
		pilot - keep the vehicle on course
	brain parts:
		hippocampus - 
		frontal cortex - 
	event-driven:
		On roll, adjust throttle
		On heading, dead reckon
		On time elapsed, 
		On position, pilot 
		On cone rounded, navigate

sources
	navigate:
	~/webapps/robots/robots/autonomy/
		hippoc.py - sim skate path around cones, with video out, using matplotlib and FuncAnimation
		nav.py - library of trigonometry used in navigation

	pilot:
	~/webapps/robots/robots/sk8mini/pilot
		pilot.ino - helm and throttle implemented via espwebserver
		pilot.py - manual piloting via keyboard as webserver client, using curses
'''
import signal
import os
import sys
import serial
import time
import argparse
import traceback
import random
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import math
import ast

import jlog
import smem
import specs
import nav

# global shared inter-process memory
gmem_timestamp = None
gmem_positions = None
args = None   # command-line arguments
captains_log = []

def setupArgParser(parser):
	# called by gcs.py before starting this process
	parser.add_argument('--port'           ,default='/dev/ttyUSB0'        ,help='serial port'                      )
	parser.add_argument('--baud'           ,default=115200    ,type=int   ,help='serial baud rate'                 )
	parser.add_argument('--serialtimeout'  ,default=3         ,type=int   ,help='serial timeout'                   )
	parser.add_argument('--serialminbytes' ,default=10        ,type=int   ,help='serial minimum bytes before read' )
	parser.add_argument('--declination'    ,default=-1.11     ,type=float ,help='# from magnetic-declination.com'  )
	parser.add_argument('--nocal'          ,action='store_true'           ,help='suppress calibration'             )
	parser.add_argument('--novideo'        ,action='store_true'           ,help='suppress UI screen save'          )
	parser.add_argument('--helmbias'       ,default=specs.helm_bias,type=int,help='helm value giving straight line')

def setupObjectModel():
	global  sensor, comm, helm, throttle, photo, arena, ui
	sensor = Sensor()
	comm = Comm()
	helm = Helm()
	throttle = Throttle()
	photo = Photo()
	arena = Arena()
	ui = UI()

class Mark:
	conendx = 0
	rdir = 'cw'
	center = [0,0]   # copy of cones[conendx]
	entry = [0,0]
	exit = [0,0]
	firstwaypt = 0
	numwaypts = 0

	def __str__(self):
		return f'{self.conendx}, {self.rdir}, {self.center}, {self.entry}, {self.exit}, {self.numwaypts}, {self.firstwaypt}'

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

class Pattern:
	name = None
	numcones = 0
	rdir = 0
	reps = 1
	firstmark = 0
	lastmark = 0
	firstwaypt = 0
	lastwaypt = 0

	def __str__(self):
		return f'{self.name}, {self.numcones}, {self.rdir}, {self.reps}, {self.firstwaypt}, {self.lastwaypt}'

	def __init__(self, name, numcones, rdir, reps):
		self.name = name
		self.numcones = numcones
		self.rdir = rdir
		self.reps = reps

class Arena:
	gate = [0,0]	# start and finish point
	cones = []	# list of points
	patterns = []	# list of Pattern objects
	marks = []	# list of Mark objects
	waypts = []	# list of points
	ndxpattern = 0	# index into patterns, current pattern
	ndxwaypt = 0	# index into waypts, current waypt
	on_mark_distance = 8
	steady_helm_distance = 12
	continuous = False

	def nextPattern(self):
		ret = False
		ndx = self.ndxpattern + 1
		if ndx <= len(self.patterns)-1:
			ret = self.patterns[ndx]
		return ret

	def currentPattern(self):return self.patterns[self.ndxpattern]
	def currentMark(self):   return self.marks[self.ndxmark]
	def currentWaypt(self):  return self.waypts[self.ndxwaypt]

	def isWayptInPattern(self, ndxwaypt, pattern): 
		return pattern.firstwaypt <= ndxwaypt <= pattern.lastwaypt
	
	def nextWaypt(self):
		if self.ndxwaypt < (len(self.waypts)-1):
			self.ndxwaypt += 1
			ui.wayptChanged = True
			if not self.isWayptInPattern(self.ndxwaypt, self.currentPattern()):
				self.ndxpattern += 1
				ui.patternChanged = True
			jlog.debug(f'nextWaypt: {self.ndxwaypt} {ui.patternChanged} {self.ndxpattern}')
			jlog.info(f'nextWaypt: {self.ndxwaypt} {self.waypts[self.ndxwaypt-1]} {self.waypts[self.ndxwaypt]} {self.waypts[self.ndxwaypt+1]}')
	
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

	def addPattern(self, name, numcones, rdir, reps):
		# create a tempory list of cone-index numbers, with a given count and order
		conendxs = None
		if type(numcones) is list: # caller has specified the list explicitly
			conendxs = list(np.array(numcones) - 1)
		else:
			if numcones == 0:
				if name == 'spin': numcones = 1
				elif name == 'oval': numcones = 2
				elif name == 'figure-8': numcones = 2
				elif name == 'barrel-race' : numcones = 3
				else: numcones = random.randrange(1, len(self.cones))
		
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

		# create a tempory list of rotational-directions, one for each cone-index
		# input rdir can be 0, 'alt', 'cw', or 'ccw'
		def alt(rdir): return 'cw' if rdir == 'ccw' else 'ccw'
		rdirs = []
		i = 0
		for ndx in conendxs:
			thisrdir = None
			if rdir in ['cw','ccw']: thisrdir = rdir  
			else: thisrdir = random.choice(['cw','ccw'])
	
			if i>0:
				if name in ['figure-8','slalom'] or rdir == 'alt':
					thisrdir = alt(rdirs[i-1])
				elif name in ['oval','perimeter']:
					thisrdir = rdirs[0]
	
			rdirs.append(thisrdir)
			i += 1
	
		# add a pattern for each rep
		if reps == 0: reps = random.randrange(1,5)
		for i in range(reps):
			pat = Pattern(name, numcones, rdir, reps)
			self.patterns.append(pat)
			jlog.info(f'add pattern {pat}')

			# create a list of marks for each pattern
			marks = []
			for j in range(len(conendxs)):
				mark = Mark(conendxs[j], rdirs[j], self.cones[conendxs[j]])
				marks.append(mark)

			# add these marks to the arena mark list
			pat.firstmark = len(self.marks)
			pat.lastmark = len(self.marks) + len(marks)
			self.marks += marks

	def recalcWaypts(self):
		r = specs.turning_radius
		gatemark = Mark.fromGate(self.gate)

		firstwaypt = arena.currentPattern().firstwaypt
		del arena.waypts[firstwaypt:]

		# loop thru patterns, starting with the current
		for ndxpat in range(arena.ndxpattern, len(arena.patterns)):
			pat = arena.patterns[ndxpat]

			if len(self.waypts) <= 0:  # first-time
				self.waypts.append( gatemark.center)  # starting gate

			pat.firstwaypt = len(self.waypts)

			# loop thru marks in each pattern
			for ndxmark in range(pat.firstmark, pat.lastmark):
				waypts = []
				mark = self.marks[ndxmark]
				mark.firstwaypt = len(self.waypts)-1

				# calc entry and exit points for each mark
				prevmark = gatemark if ndxmark <= 0 else self.marks[ndxmark-1]
				nextmark = gatemark if ndxmark+1 >= len(self.marks) else self.marks[ndxmark+1] 
		
				A = prevmark.center
				B = mark.center
				L, R = nav.linePerpendicular(A, B, r)
				entry = {
					'L': L,
					'R': R,
				}
			
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
	
				# calc waypts for each mark
				thetaEntry,_ = nav.thetaFromPoint(mark.entry, mark.center)
				thetaExit,_ = nav.thetaFromPoint(mark.exit, mark.center)
				thetaDiff = nav.lengthOfArcTheta(thetaEntry, thetaExit, mark.rdir)
	
				thetaPre = (thetaEntry + .5) % math.tau
				thetaPost = (thetaExit - .5) % math.tau
				if mark.rdir == 'ccw':
					thetaPre = (thetaEntry - .5) % math.tau
					thetaPost = (thetaExit + .5) % math.tau
	
				preentry = nav.pointFromTheta(mark.center, thetaPre, specs.turning_radius*1.5)
				waypts.append( preentry)
				n = int(thetaDiff/(math.pi/2))
				thetaIncr = thetaDiff / (n+1)
				for mult in range(1, n+1):
					if mark.rdir == 'cw':
						thetaEx = (thetaEntry - (thetaIncr*mult)) % math.tau
					else:
						thetaEx = (thetaEntry + (thetaIncr*mult)) % math.tau
					intermediate = nav.pointFromTheta(mark.center, thetaEx, specs.turning_radius)
					waypts.append( intermediate)
	
				postexit = nav.pointFromTheta(mark.center, thetaPost, specs.turning_radius*1.5)
				waypts.append( postexit)

				self.waypts += waypts   # add these waypts to master list
				mark.lastwaypt = len(self.waypts)-1  # last for the mark
	
			if (not self.continuous) and (ndxpat >= len(self.patterns)-1): # last time
				self.waypts.append( gatemark.center)  # finish gate

			pat.lastwaypt = len(self.waypts)-1  # last for the pattern
		ui.patternChanged = True
		jloglist(self.patterns)

class Sensor:
	heading	= 9999.0
	roll	= 0.0
	pitch	= 0.0
	sys	= 0
	gyro	= 0
	accel	= 0
	mag	= 0
	t	= 0

class Helm:
	helm = 0
	biased_helm = 0
	rudder = 0
	t = 0.0
	incr = 2

	def set(self, val):
		self.helm = val
		self.biased_helm = min(90, max(-90, self.helm + args.helmbias))
		self.t = time.time()
		comm.sendCommand(comm.HELM, self.biased_helm)

	def incStarboard(self):
		self.helm = val + self.incr
		self.biased_helm = min(90, max(-90, self.helm + args.helmbias))
		self.t = time.time()
		comm.sendCommand(comm.HELM(self.biased_helm))

	def incPort(self):
		self.helm = val - self.incr
		self.biased_helm = min(90, max(-90, self.helm + args.helmbias))
		self.t = time.time()
		comm.sendCommand(comm.HELM(self.biased_helm))

class Throttle:
	throttle = 0
	right_throttle = 0 
	paused = False
	STOP = 0
	CRUISE = 23
	FULL = 43
	autopilot = True
	t = 0.0
	def set(self, val):
		self.throttle = max(0, min(self.FULL, val))
		self.right_throttle = self.throttle # * rudder factor
		self.t = time.time()
		comm.sendCommand(comm.THROTTLE, self.right_throttle)
	def isPaused(self): 
		return self.paused
	def pause(self): 
		self.paused = True
		comm.sendCommand(comm.THROTTLE, self.STOP)
	def unpause(self): 
		self.paused = False
		comm.sendCommand(comm.THROTTLE, self.CRUISE)

class Photo:
	MAXTIME = 3.0 # seconds
	donut = [0,0]
	cbase = [0,0]
	cones = [0,0]
	t = 0.0
	def hasNewPhoto(self): return (gmem_timestamp[smem.TIME_PHOTO] > self.t)
	def isPhotoLate(self): return (gmem_timestamp[smem.TIME_PHOTO] <= self.t) and ((time.time() - self.t) > self.MAXTIME)

# ----------------------------------------
#    comm
# ----------------------------------------

class Comm:
	openSettleTime = .5  # why?
	sendSettleTime = .2  # .9 fails  timeout on the read side?
	tsend = 0.0
	serial_port = False	# instantiation of Serial object
	HELM	= 1 # val = -90 to +90, negative:port, positive:starboard, zero:amidships
	THROTTLE= 2 # val = -90 to +90, negative:astern, positive:ahead, zero:stop

	def connectSerial(self):
		try:
			self.serial_port = serial.Serial(port=args.port, baudrate=args.baud, timeout=args.serialtimeout)
		except:
			return False
		time.sleep(self.openSettleTime)  # why?
		return True

	def sendCommand(self, cmd, value):
		if self.serial_port and self.serial_port.isOpen():
			settleTime = self.sendSettleTime - (time.time() - self.tsend)
			if settleTime > 0:
				time.sleep(settleTime)
			s = f'{cmd}\t{value}\n' 
			self.serial_port.write(bytes(s, 'utf-8'))
			self.tsend = time.time()
			jlog.debug(f'command sent to sk8: {s.strip()}')
		else:
			jlog.debug(f'command not sent, no serial port: {s.strip()}')

	def recvSensor(self):
		lst = [1,2]
		if len(lst) != 7:
			comm.serial_port.reset_input_buffer() # make sure we get the latest message
			b = comm.serial_port.readline()	# serial read to \n or timeout, whichever comes first
			s = b.decode("utf-8")	# to tab-separated string
			lst = s.split()		# parse into object
			if len(lst) != 7:
				jlog.info(f'incomplete serial sensor message ignored {len(lst)}')
				return
	
		sensor.heading	= float( lst[0])
		sensor.roll	= float( lst[1])
		sensor.pitch	= float( lst[2])
		sensor.sys	= int( lst[3])
		sensor.gyro	= int( lst[4])
		sensor.accel	= int( lst[5])
		sensor.mag	= int( lst[6])
		sensor.t	= time.time()
		jlog.debug(f'lenstr:{len(b)}, lenlst:{len(lst)}, heading:{sensor.heading:.2f}, roll:{sensor.roll:.2f}, gyro:{sensor.gyro}, mag:{sensor.mag}')
	
		# the BRO055 does NOT adjust for magnetic declination, so we do that here
		adjheading = sensor.heading + args.declination
		if adjheading < 0:
			adjheading = (360 - adjheading)
		sensor.heading = adjheading

# ----------------------------------------
#    navigator
# ----------------------------------------

def formatPoint(pt):
	return f'[{pt[0]:.2f}, {pt[1]:.2f}]'

def calcCenterWheelbase(donut):
	theta = nav.thetaFromHeading((sensor.heading + helm.helm + 180) % 360)
	cbase = nav.pointFromTheta( donut, theta, specs.helm_length)
	jlog.info(f'calcCenterWheelBase {sensor.heading:.2f} {helm.helm:.2f}; {theta:.2f}, {formatPoint(donut)}, {formatPoint(cbase)}')
	# we should also apply the helm_offset and roll_y_offset
	return cbase

def getPhoto():  # get positions of donut, cones from shared memory, calc cbase position
	photo.donut = specs.awacs2skate([gmem_positions[smem.DONUT_X], gmem_positions[smem.DONUT_Y]])
	photo.cbase = calcCenterWheelbase(photo.donut)
	photo.cones = getCones()
	photo.t = gmem_timestamp[smem.TIME_PHOTO]
	ui.cbaseChanged = True

def getCones():
	cones = []
	numcones = gmem_positions[smem.NUM_CONES]
	pos = smem.CONE1_X
	for i in range(numcones):
		pt = [gmem_positions[pos], gmem_positions[pos+1]]
		cone = specs.awacs2skate(pt)
		cones.append(cone)
		pos += 2
	return list(sorted(cones))
	
def convertLine(line):
	spat, sncones, srdir, sreps = line.split(', ')
	pat = int(spat) if spat.isnumeric() else spat
	ncones = ast.literal_eval(sncones) if sncones[0] == '[' else int(sncones)
	rdir = srdir if srdir in ['cw', 'ccw'] else int(srdir)
	reps = int(sreps) 
	return pat, ncones, rdir, reps

def configArena():
	arena.cones = photo.cones
	arena.gate = photo.cbase

	jlog.debug(f'cones: {arena.cones}')
	jlog.debug(f'donut: {photo.donut}')
	jlog.debug(f'cbase: {photo.cbase}')
	jlog.debug(f'gate:  {arena.gate}')

	# read patterns from filename
	fname = f'{args.mediaout}/../pattern.txt'
	try:
		with open(fname) as fp:
			for line in fp:
				if line[0] == '#':
					continue
				name, ncones, rdir, reps = convertLine(line)
				if name == 'continue':
					arena.addPattern(0,0,0,1)
					arena.continuous = True
				else:
					arena.addPattern(name, ncones, rdir, reps)
			arena.recalcWaypts()
	except FileNotFoundError:
		arena.addPattern(0,0,0,1)
		arena.addPattern(0,0,0,1)
		arena.recalcWaypts()
		arena.continuous = True

# ----------------------------------------
#    pilot
# ----------------------------------------

def normalizeTheta(tfrom, tto, tat, rdir):
	tcirc = 2*np.pi
	if rdir == 'ccw':
		ntat = (tat - tfrom) % tcirc
		ntto = (tto - tfrom) % tcirc
	elif rdir == 'cw':
		ntat = tcirc - ((tat - tfrom) % tcirc)
		ntto = tcirc - ((tto - tfrom) % tcirc)
	if ntat > 5.5:
		ntat = 0.001
	return ntat, ntto

def distanceToDest(cbase, leg):
	# assume leg['shape'] == 'line':
	tot = nav.lengthOfLine(leg['to'], leg['from'])
	sofar = nav.lengthOfLine(cbase, leg['from'])
	togo = tot - sofar
	return togo

#def isOnMark(cbase, leg):
#	on_mark = False
#	if leg['shape'] == 'line':
#		#err = nav.lengthOfLine(cbase, leg['to'])
#		#on_mark = (err < arena.on_mark_distance)
#		#jlog.info(f'on mark line {on_mark} {arena.routendx}, {err} {cbase} {leg["to"]}')
#
#		tot = nav.lengthOfLine(leg['to'], leg['from'])
#		sofar = nav.lengthOfLine(cbase, leg['from'])
#		on_mark = sofar > tot
#		jlog.info(f'on mark line {on_mark} {arena.routendx}, {tot} {sofar} {cbase} {leg["to"]}')
#	
#	elif leg['shape'] == 'arc':
#		# here using theta in radians
#		tbase,_ = nav.thetaFromPoint(cbase, leg['center'])
#		tto,_ = nav.thetaFromPoint(leg['to'], leg['center'])
#		tfrom,_ = nav.thetaFromPoint(leg['from'], leg['center'])
#		ntbase,ntto = normalizeTheta(tfrom, tto, tbase, leg['rdir'])
#		on_mark = (ntbase > ntto)
#		jlog.info(f'on mark arc {on_mark} {arena.routendx}, tbase:{tbase} tfrom:{tfrom} tto:{tto} rdir:{leg["rdir"]}')
#	return on_mark

def isOnMark(cbase):
	on_mark = False
	tot = nav.lengthOfLine(arena.waypts[arena.ndxwaypt], arena.waypts[arena.ndxwaypt-1])
	sofar = nav.lengthOfLine(cbase, arena.waypts[arena.ndxwaypt-1])
	on_mark = sofar > tot
	return on_mark

def helmPid(error):  # pid control of steering
	# see https://docs.google.com/spreadsheets/d/1oKY4mz-0K-BwVNZ7Tu-k9PsOq_LeORR270-ICXyz-Rw/edit#gid=0
	jlog.debug('helm PID')
	Kp = 2
	Ki = 0
	Kd = 0
	helmadj = Kp * error
	helmadj = max(-90,min(90,helmadj))
	return helmadj

#
# ------------------
# 

caplogheader = False
def caplog():
	global caplogheader
	if not caplogheader:
		s = f'log\tcbase\tt\thelm\tthrottle\theading\troll'
		jlog.info(s)
		caplogheader = True
	s = f'log\t{formatPoint(photo.cbase)}\t{photo.t:.2f}\t{helm.helm:.2f}\t{throttle.throttle:.2f}\t{sensor.heading:.2f}\t{sensor.roll:.2f}'
	captains_log.append(s)
	jlog.info(s)

def readLogByDate(ts):
	ndx = len(captains_log) - 1
	leasterr = 9999
	leastndx = ndx
	while ndx > 0:
		err = captains_log[ndx]['starttime'] - ts	
		if err < leasterr:
			leasterr = err
			leastndx = ndx
		else:
			break
		ndx -= 1
	return captains_log[leastndx]

def pilot():
	jlog.debug(f'in pilot')
	position_changed = False

	# first time
	if arena.ndxwaypt <= 0:
		throttle.set( throttle.CRUISE)
		arena.nextWaypt()

	# get new position
	if photo.hasNewPhoto():	
		getPhoto()

	if not throttle.autopilot:
		return

	# on rounding mark
	tot = nav.lengthOfLine(arena.waypts[arena.ndxwaypt], arena.waypts[arena.ndxwaypt-1])
	sofar = nav.lengthOfLine(photo.cbase, arena.waypts[arena.ndxwaypt-1])
	if (sofar+arena.on_mark_distance) > tot:
		if arena.ndxwaypt >= len(arena.waypts) - 1:  # journey's end
			kill('route completed')
			return
		else:
			arena.nextWaypt()

	# stay on course
	#elif sofar > (tot - arena.steady_helm_distance):
	bearing = nav.headingOfLine(photo.cbase, arena.waypts[arena.ndxwaypt])
	error = bearing - sensor.heading
	if error > 180:
		error -= 360
	if error < -180:
		error += 360
	helm_adj = helmPid( error)
	jlog.info(f'pilot: new helm line:{helm_adj}, err:{error}, bearing:{bearing}, heading:{sensor.heading}')
	helm.set( helm_adj)

	caplog()

	#if arena.continuous and (arena.ndxwaypt >= len(arena.waypts))-3:
	if arena.continuous and (arena.ndxpattern >= len(arena.patterns)-1):
		arena.addPattern(0,0,0,1) 
		arena.recalcWaypts() 

# ----------------------------------------
#    UI
# ----------------------------------------

class UI:
	fig = None
	ax = None
	skateline = None
	wayline = None
	nextline = None
	cones = []
	conerings = []
	conetexts = []
	legs = []
	conesChanged = True
	cbaseChanged = True
	wayptChanged = True
	patternChanged = True
	t = 0.0
	eventkey = False
	fps = 0
	delay = 0
	PAUSE = .001
	fname = ''

def onpress(event):
	ui.eventkey = event.key

def startUI():
	ui.fps = 20
	ui.delay = 1/ui.fps  # .05
	ui.fname = f'{args.mediaout}/arena_%timestamp%.png'

	# setup artists
	ui.fig = plt.figure()
	ui.ax = ui.fig.add_axes((0,0,1,1))

	plt.xlim(-132,+132)
	plt.ylim(-132,+132)

	plt.autoscale(False)  # if True it will adapt x,ylim to the data
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	ui.ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize

	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False) 
	plt.tick_params(axis='y', which='both', right=False, left=False, labelleft=False) 

	ui.fig.set_size_inches(6,6)  # savefig with dpi=100, for a 600x600 image to match aerial
	mpl.rcParams['savefig.dpi'] = 100
	mpl.rcParams['savefig.pad_inches'] = 0.0
	mpl.rcParams['savefig.transparent'] = True
	mpl.rcParams['savefig.bbox'] = 'tight'

	ui.fig.canvas.mpl_connect('key_press_event', onpress) # keypress event handler

	# cones in cone order left to right
	for pt in arena.cones:
		circ = plt.Circle(pt, specs.cone_diameter/2, color='y')
		ui.ax.add_artist(circ)
		ui.cones.append(circ)
		circ = plt.Circle(pt, specs.turning_radius, fill=False, color='y')
		ui.ax.add_artist(circ)
		ui.conerings.append(circ)
		textnum = str(len(ui.cones)) # left to right
		t = plt.text(pt[0], pt[1], textnum, fontsize='12', ha='center', va='center', color='black')
		ui.conetexts.append(t)
		ui.conesChanged = True
		
	# line connecting waypoints
	x,y = np.array(arena.waypts).T
	ui.nextline, = ui.ax.plot(x,y, linestyle='-', marker='.', color='b', linewidth=.5)
	ui.wayline, = ui.ax.plot(x,y, linestyle='-', marker='.', color='b')

	# current waypoint
	ui.hiway, = ui.ax.plot([0,0],[0,0], color='r')

	# sprite
	ui.sprite = mpl.patches.Polygon(specs.skateSprite, facecolor='none', edgecolor='black')
	ui.ax.add_patch(ui.sprite)

	# donut
	ui.donutouter = plt.Circle(photo.donut, specs.donut_outer_dia/2, facecolor='white', edgecolor='black')
	ui.donutinner = plt.Circle(photo.donut, specs.donut_inner_dia/2, color='magenta')
	ui.ax.add_artist(ui.donutouter)
	ui.ax.add_artist(ui.donutinner)

	# gate
	w = arena.on_mark_distance
	h = arena.on_mark_distance
	anchor = (photo.cbase[0]-(w/2), photo.cbase[1]-(h/2))
	ui.gate = plt.Rectangle(anchor, w, h, color='black', fill=False)
	ui.ax.add_artist(ui.gate)

	ui.cbaseChanged = True

def refreshUI():
	if time.time() - ui.t >= ui.delay:  # slow down to desired fps
		jlog.debug(f'inside refresuUI, {ui.conesChanged}, {ui.cbaseChanged}, {ui.wayptChanged}, {ui.patternChanged}')

		# first, adjust the data that defines the shape
		# second, call plt.pause() which does the drawing
		if ui.conesChanged:
			i = 0
			for i in range(len(ui.cones)):
				ui.cones[i].center = arena.cones[i]
				ui.conerings[i].center = arena.cones[i]
				ui.conetexts[i]._x = arena.cones[i][0]
				ui.conetexts[i]._y = arena.cones[i][1]
			ui.conesChanged = False
	
		if ui.patternChanged:
			pat = arena.currentPattern()
			points = arena.waypts[pat.firstwaypt:pat.lastwaypt+2]
			points = np.transpose(points) 
			ui.wayline.set_data(points)

			pat = arena.nextPattern()
			if pat:
				points = arena.waypts[pat.firstwaypt:pat.lastwaypt+2]
				points = np.transpose(points) 
			else:
				points = [[0,0],[0,0]]
			ui.nextline.set_data(points)

			ui.patternChanged = False
	
		if ui.wayptChanged:
			end = max(0, arena.ndxwaypt)
			end = min(end, len(arena.waypts)-1)
			start = max(0, end-1)
			hiway = np.transpose([arena.waypts[start], arena.waypts[end]])
			ui.hiway.set_data(hiway)
			ui.wayptChanged = False

		if ui.cbaseChanged:
			# sprite
			r = mpl.transforms.Affine2D().rotate_deg(360-sensor.heading)
			t = mpl.transforms.Affine2D().translate(photo.cbase[0], photo.cbase[1])
			tra = r + t + ui.ax.transData
			ui.sprite.set_transform(tra)

			# donut
			ui.donutinner.center = photo.donut
			ui.donutouter.center = photo.donut

			ui.cbaseChanged = False

			if not args.novideo:
				timestamp = time.time()
				stime = f'{jlog.selapsed()}'.replace('.','_')
				fname = f'{args.mediaout}/{stime}.png'
				ui.fig.savefig(fname)
				jlog.debug(f'UI: screen capture {fname}')

		ui.t = time.time()

	plt.pause(ui.PAUSE)  # redraw and time.sleep()

def respondToKeyboard():
	key = ui.eventkey
	ui.eventkey = False

	if key == 'q':
		kill('UI: kill')

	elif key == 'ctrl+c':
		kill('UI: kill interrupt')

	elif key == 'c':
		ts = time.strftime("%Y%m%d-%H%M%S")

		stime = f'{timestamp:.2f}'.replace('.','_')
		fname = f'{dirname}/{stime}.{imgext}'

		ui.fig.savefig(fname.replace('%timestamp%', ts))
		jlog.info(f'UI: screen capture {ts}')

	elif key == 'a':
		throttle.autopilot = True
		jlog.info(f'UI: autopilot on')

	elif key == 'o':
		throttle.autopilot = False
		jlog.info(f'UI: autopilot off')

	elif key == 'left':
		throttle.autopilot = False
		helm.incrPort()
		jlog.info(f'UI: helm port {helm_incr} degree: {helm.helm} {sensor.roll}')

	elif key == 'right':
		throttle.autopilot = False
		helm.incrStarboar()
		jlog.info(f'UI: helm starboard {helm_incr} degree: {helm.helm} {sensor.roll}')

	elif key == 'up':
		newhelm = 0
		helm.set(0)	
		jlog.info('UI: helm amidships')

	elif key == 'r':
		configArena()
		jlog.info('UI: reconfigure arena')

	elif key == 'w':
		arena.nextWaypt()
		jlog.info('UI: next waypt')

	return key

# ----------------------------------------
#    process target
# ----------------------------------------

def kill(msg):
	gmem_timestamp[smem.TIME_KILLED] = time.time()
	jlog.info(f'kill: {msg}')

def isKilled():
	return (gmem_timestamp[smem.TIME_KILLED] > 0)
	
def jloglist(olist): 
	for o in olist: jlog.info(o)

def skate_main(timestamp, positions):
	global gmem_timestamp, gmem_positions
	try:
		jlog.setup('skate', args.verbose, args.quiet, args.mediaout)
		jlog.info(f'starting process id: {os.getpid()}')
		gmem_timestamp = timestamp
		gmem_positions = positions
		setupObjectModel()
		jlog.info(f'object model initialized')

		if args.sim:
			photo.donut = [-130, -130]
			photo.cbase = [-120, -120]
			photo.cones = specs.vcones['iron-cross']
			sensor.heading = 5
	
			configArena()

			jloglist(arena.patterns)
			jloglist(arena.waypts)

			startUI()
			while True:
				if isKilled():
					break
				refreshUI()
				key = respondToKeyboard()

				# copy from pilot()
				if arena.continuous and (arena.ndxpattern >= len(arena.patterns)-1):
					arena.addPattern(0,0,0,1) 
					arena.recalcWaypts() 
			quit()

		# ignore KeyboardInterrupt, leave for gcs
		signal.signal(signal.SIGINT, signal.SIG_IGN)

		# serial port
		rc = comm.connectSerial()
		if not rc:
			kill(f'serial port {args.port} connection failed')
			return
		jlog.info(f'serial port {args.port} connected')

		# setup loop
		calibrated	= False
		arena_ready	= False
		ui_ready	= False
		user_go	= False
		while True:
			if isKilled():
				jlog.info(f'stopping setup loop due to kill')
				break

			comm.recvSensor()

			if not calibrated:
				jlog.info('calibrating...')
				if sensor.mag >= 3 and sensor.gyro >= 3:
					jlog.info('sensor calibrated')
					calibrated = True

			elif not arena_ready:
				if photo.hasNewPhoto():
					getPhoto()
					configArena()
					jlog.info('arena configured')
					arena_ready = True

			elif not ui_ready:
					startUI()
					refreshUI()
					ui_ready = True
					jlog.debug('click g to go')

			elif not user_go:
				refreshUI()
				key = respondToKeyboard()
				if key == 'g':
					user_go = True

			else:
				jlog.info('go')
				break

		# main loop
		while True:
			if isKilled():
				jlog.info(f'stopping main loop due to kill')
				break

			comm.recvSensor()

			if photo.hasNewPhoto():
				jlog.debug(f'has photo')
				if throttle.isPaused():
					throttle.unpause()
				pilot()	

			elif photo.isPhotoLate():
				throttle.pause()

			refreshUI()
			if ui.eventkey:
				key = respondToKeyboard()

	except KeyboardInterrupt:
		jlog.error('never happen')

	finally:
		kill('finally')
		if comm.serial_port and comm.serial_port.isOpen():
			throttle.set(0)
			helm.set(0)
			comm.serial_port.close()
	jlog.info(f'main exit')

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--sim'      ,action='store_true'  ,help='simulation mode'                  ) 
	parser.add_argument('--verbose'  ,action='store_true'  ,help='verbose comments'                 ) 
	parser.add_argument('--quiet'    ,action='store_true'  ,help='suppress all output'              )
	parser.add_argument('--mediaout' ,default='/home/john/media/webapps/sk8mini/awacs/photos' ,help='folder out for images, log')
	setupArgParser(parser)
	args = parser.parse_args() # returns Namespace object, use dot-notation

	args.mediaout = f'{args.mediaout}/{time.strftime("%Y%m%d-%H%M%S")}'
	os.mkdir(args.mediaout)

	import multiprocessing
	smem_timestamp = multiprocessing.Array('d', smem.TIME_ARRAY_SIZE) # initialized with zeros
	smem_positions = multiprocessing.Array('i', smem.POS_ARRAY_SIZE)  # initialized with zeros
	skate_main(smem_timestamp, smem_positions)

