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

to do:
        1. Count rpm at each speed setting
        2. Measure actual distance and time 
                x Get photo save working
                x Get pilot commands working
        3.  Math circum of turning radius,
                throttle, throttle left, throttle right

add onRoll: adjust right-throttle
	write math to adjust throttle depending on roll

finish figure 8 pattern for calibration, with right throttle adjustment

dead reckoning
	keep list of recent commands
	with each new command, calc new position by adding previous command

who sets up the arena, pilot?  navigator?, captain?

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

class Arena:
	gate = [0,0]
	cones = []
	plan = []
	route = []
	routendx = []
	leg = {}
	on_mark_distance = 8

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

def configArena():
	arena.cones = photo.cones
	arena.gate = photo.cbase

	jlog.debug(f'cones: {arena.cones}')
	jlog.debug(f'donut: {photo.donut}')
	jlog.debug(f'cbase: {photo.cbase}')
	jlog.debug(f'gate:  {arena.gate}')

	# route: plan, calc, plot
	order, sides = planRoute(arena.cones)
	#order = [0,1]
	#sides = ['cw', 'cw']
	jlog.debug(f'order: {order}, sides: {sides}')

	arena.plan = calcPlan(arena.cones, order, sides)
	jlog.debug(f'plan: {arena.plan}')

	arena.route = plotRoute(arena.plan)
	arena.routendx = -1
	jlog.debug(f'route: {arena.route}')

def planRoute(cones):
	order = []
	for i in range(len(cones)):
		order.append(i)
	random.shuffle(order)
	
	sides = []
	for cone in cones:
		rdir = np.random.choice(['ccw','cw'])
		sides.append(rdir)
	return order, sides
	
def calcPlan(cones, order, sides):
	# combine cones, order, sides into a list of dicts, sorted by order
	plan = []
	for i in range(len(order)):
		plan.append({
			'order':order[i], 
			'center':cones[i], 
			'rdir':sides[i], 
		})
	plan = sorted(plan, key=lambda cone: cone['order'])

	# add entry and exit points to each cone
	r = specs.turning_radius
	localgate = { 'center': arena.gate }
	for i in range(len(plan)):
		cone = plan[i]
		prevcone = localgate if i <= 0 else plan[i-1]
		nextcone = localgate if i+1 >= len(plan) else plan[i+1] 

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
	return plan
	
def plotRoute(plan):
	route = []
	prevexit = arena.gate
	for i in range(0,len(plan)):
		cone = plan[i]

		route.append({
			'shape': 'line',
			'from': prevexit,
			'to': cone['entry'],
			'center': cone['center'],
			'rdir': cone['rdir'],
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
	jlog.debug(f'back to starting gate: {prevexit}, {arena.gate}')
	route.append({
		'shape': 'line',
		'from': prevexit,
		'to': arena.gate,
	})
	return route

# ----------------------------------------
#    pilot
# ----------------------------------------

def nextLeg():
	arena.routendx += 1
	arena.leg = arena.route[arena.routendx]

	jlog.info(f'next leg {arena.routendx}: {arena.leg}')

	if arena.leg['shape'] == 'arc':
		if arena.leg['rdir'] == 'cw':
			helm.set( +90)
		elif arena.leg['rdir'] == 'ccw':
			helm.set( -90)
	elif arena.leg['shape'] == 'line':
		helm.set( 0)

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

def isOnMark(cbase, leg):
	on_mark = False
	if leg['shape'] == 'line':
		err = nav.lengthOfLine(cbase, leg['to'])
		on_mark = (err < arena.on_mark_distance)
		jlog.info(f'on mark line {on_mark} {arena.routendx}, {err} {cbase} {leg["to"]}')
	
	elif leg['shape'] == 'arc':
		# here using theta in radians
		tbase,_ = nav.thetaFromPoint(cbase, leg['center'])
		tto,_ = nav.thetaFromPoint(leg['to'], leg['center'])
		tfrom,_ = nav.thetaFromPoint(leg['from'], leg['center'])
		ntbase,ntto = normalizeTheta(tfrom, tto, tbase, leg['rdir'])
		on_mark = (ntbase > ntto)
		jlog.info(f'on mark arc {on_mark} {arena.routendx}, tbase:{tbase} tfrom:{tfrom} tto:{tto} rdir:{leg["rdir"]}')
	return on_mark

def helmpid(err): # pid control of steering
	# see https://docs.google.com/spreadsheets/d/1oKY4mz-0K-BwVNZ7Tu-k9PsOq_LeORR270-ICXyz-Rw/edit#gid=0
	jlog.debug('helm pid')
	Kp = 2
	adj = Kp * err
	adj = max(-90,min(90,adj))
	return adj

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
	if arena.routendx == -1:
		throttle.set( throttle.CRUISE)
		nextLeg()

	# get new position
	if photo.hasNewPhoto():	
		getPhoto()

	if not throttle.autopilot:
		return

	# on rounding mark
	if isOnMark(photo.cbase, arena.leg):
		if arena.routendx >= len(arena.route) - 1:  # journey's end
			throttle.set(throttle.STOP)
			helm.set(0)
			kill('route completed')
			return
		else:
			nextLeg()

	# stay on course
	if arena.leg['shape'] == 'line':
		bearing = nav.headingOfLine(photo.cbase, arena.leg['to'])
		error = bearing - sensor.heading
		if error > 180:
			error -= 360
		if error < -180:
			error += 360
		helm_adj = helmpid( error)
		jlog.info(f'pilot: new helm line:{helm_adj}, err:{error}, bearing:{bearing}, heading:{sensor.heading}')
		helm.set( helm_adj)

	elif arena.leg['shape'] == 'arc':
		jlog.debug(f'pilot: not helm arc, heading:{sensor.heading}, cbase:{photo.cbase}, leg-to:{arena.leg["to"]}')

	caplog()

# ----------------------------------------
#    UI
# ----------------------------------------

class UI:
	fig = None
	ax = None
	skateline = None
	cones = []
	conetexts = []
	legs = []
	conesChanged = True
	routeChanged = True
	cbaseChanged = True
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
		textnum = str(len(ui.cones)) # left to right
		t = plt.text(pt[0], pt[1], textnum, fontsize='12', ha='center', va='center', color='black')
		ui.conetexts.append(t)
		ui.conesChanged = True
		
	# legs
	for leg in arena.route:

		if leg['shape'] == 'line':
			A = (leg['from'])
			B = (leg['to'])
			xd,yd = np.transpose([A,B]); 
			linesegs = plt.plot(xd,yd, color='blue', lw=1) # returns list of line2D objects
			ui.legs.append(linesegs[0])

		elif leg['shape'] == 'arc':
			# in matplotlib, Arc subclasses Ellipse
			# define Ellipse as center, width, height, angle:
			C = (leg['center'])       # center x,y
			r = specs.turning_radius  # width and height, both r, angle=0

			# add two points to define the Arc along the ellipse
			A = (leg['from'])
			B = (leg['to'])
			tA,_ = nav.thetaFromPoint(A, C)
			tB,_ = nav.thetaFromPoint(B, C)
			rdir = leg['rdir']

			# in matplotlib, the Arc must be drawn ccw
			# in a skateRouteLeg, the arc can be traversed either cw or ccw
			# ergo, when drawing, we draw a cw arc backwards
			t1 = tA
			t2 = tB
			if rdir == 'cw': 
				t1 = tB # reverse
				t2 = tA
				if t1 == t2: # ? avoid full circle ?
					t2 -= .001

			arc = mpl.patches.Arc(C, r*2, r*2, 0, math.degrees(t1), math.degrees(t2), color='blue')

			ui.ax.add_patch(arc)
			ui.legs.append(arc)

		ui.routeChanged = True

	# skate
	#ui.skateline = ui.ax.scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])

	# sprite
	ui.sprite = mpl.patches.Polygon(specs.skateSprite, facecolor='none', edgecolor='black')
	ui.ax.add_patch(ui.sprite)

	# donut
	ui.donutouter = plt.Circle(photo.donut, specs.donut_outer_dia/2, facecolor='white', edgecolor='black')
	ui.donutinner = plt.Circle(photo.donut, specs.donut_inner_dia/2, color='magenta')
	ui.ax.add_artist(ui.donutouter)
	ui.ax.add_artist(ui.donutinner)

	# cbase
	#ui.cbase = plt.Circle(photo.donut, 3, color='black')
	#ui.ax.add_artist(ui.cbase)

	ui.cbaseChanged = True

def refreshUI():
	jlog.debug(f'refresuUI, {time.time()}, {ui.t}')
	if time.time() - ui.t >= ui.delay:  # slow down to desired fps
		jlog.debug(f'inside refresuUI, {ui.conesChanged}, {ui.routeChanged}, {ui.cbaseChanged}')

		# first, adjust the data that defines the shape
		# second, call plt.pause() which does the drawing
		if ui.conesChanged:
			i = 0
			for i in range(len(ui.cones)):
				ui.cones[i].center = arena.cones[i]
				ui.conetexts[i]._x = arena.cones[i][0]
				ui.conetexts[i]._y = arena.cones[i][1]
			ui.conesChanged = False
	
		if ui.routeChanged:
			# for a line, change the two end points
			for i in range(len(arena.route)):
				leg = arena.route[i]
				if leg['shape'] == 'line':
					A = (leg['from'])
					B = (leg['to'])
					xd,yd = np.transpose([A,B]); 
					ui.legs[i].set_data(xd,yd)

			# for an arc, change center and two thetas
			for leg in arena.route:
				if leg['shape'] == 'arc':
					C = (leg['center'])

					if leg['rdir'] == 'ccw':
						A = (leg['from'])
						B = (leg['to'])
					else:
						B = (leg['from'])
						A = (leg['to'])

					tA,_ = nav.thetaFromPoint(A, C)
					tB,_ = nav.thetaFromPoint(B, C)

					ui.legs[i].center = C
					ui.legs[i].theta1 = tA
					ui.legs[i].theta2 = tB

			ui.routeChanged = False
	
		if ui.cbaseChanged:
			# skateline
			#bow,stern = nav.lineFromHeading(cbase, heading, specs.deck_length/2)
	#		bow,stern = nav.lineFromHeading(photo.cbase, sensor.heading, specs.deck_length)
	#		diff = (bow - stern) / 5  # add 4 dots between bow and stern
	#		points = [[0,0],[0,0],[0,0],[0,0],[0,0]]
	#		for i in range(5): points[i] = stern + (np.array(diff) * i)
	#		#points = np.transpose(points); 
	#		ui.skateline.set_offsets(points)

			# cbase sprite
			r = mpl.transforms.Affine2D().rotate_deg(360-sensor.heading)
			t = mpl.transforms.Affine2D().translate(photo.cbase[0], photo.cbase[1])
			tra = r + t + ui.ax.transData
			ui.sprite.set_transform(tra)

			# donut
			ui.donutinner.center = photo.donut
			ui.donutouter.center = photo.donut

			# cbase
	#		ui.cbase.center = photo.cbase

			ui.cbaseChanged = False

			if not args.novideo:
				timestamp = time.time()
				stime = f'{jlog.selapsed()}'.replace('.','_')
				fname = f'{args.mediaout}/{stime}.png'
				ui.fig.savefig(fname)
				jlog.debug(f'UI: screen capture {fname}')

		ui.t = time.time()

	jlog.debug(f'plt pause')
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

	return key

# ----------------------------------------
#    process target
# ----------------------------------------

def kill(msg):
	gmem_timestamp[smem.TIME_KILLED] = time.time()
	jlog.info(f'kill: {msg}')

def isKilled():
	return (gmem_timestamp[smem.TIME_KILLED] > 0)
	
def skate_main(timestamp, positions):
	global gmem_timestamp, gmem_positions
	try:
		jlog.setup('skate', args.verbose, args.quiet, args.mediaout)
		jlog.info(f'starting process id: {os.getpid()}')
		gmem_timestamp = timestamp
		gmem_positions = positions
		signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore KeyboardInterrupt
		setupObjectModel()

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

