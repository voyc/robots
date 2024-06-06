'''
skate.py - skate library imported by gcs.py

runs in the skate_process, launched by gcs.py 
communicates with sk8.ino

functions:
	on startup, calibrate the BRO055 sensor
	receive AHRS data sk8 via serial port dongle running gcs.ino
	receive donut center from awacs
	calculate wheelbase center by combining donut center, helm angle, roll angle
	navigate
	pilot
	send pilot commands to sk8 through the serial port dongle

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
---------------
sources

navigate:
	~/webapps/robots/robots/autonomy/
		hippoc.py - sim skate path around cones, with video out, using matplotlib and FuncAnimation
		nav.py - library of trigonometry used in navigation

pilot:
	~/webapps/robots/robots/sk8mini/pilot
		pilot.ino - helm and throttle implemented via espwebserver
		pilot.py - manual piloting via keyboard as webserver client, using curses

---------------

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

import jlog
from smem import *
import specs
import nav

def setupArgParser(parser):
	parser.add_argument('--port'           ,default='/dev/ttyUSB0'        ,help='serial port'                      )
	parser.add_argument('--baud'           ,default=115200    ,type=int   ,help='serial baud rate'                 )
	parser.add_argument('--serialtimeout'  ,default=3         ,type=int   ,help='serial timeout'                   )
	parser.add_argument('--serialminbytes' ,default=10        ,type=int   ,help='serial minimum bytes before read' )
	parser.add_argument('--declination'    ,default=-1.11     ,type=float ,help='# from magnetic-declination.com'  )
	parser.add_argument('--nocal'          ,action='store_true'           ,help='suppress calibration'             )

# the following globals are set during startup BEFORE the process starts
args = None   # command-line arguments

# types
class AHRS:
	heading	= 9999.0
	roll	= 0.0
	pitch	= 0.0
	sys	= 0
	gyro	= 0
	accel	= 0
	mag	= 0

# global constants
# a command contains two integers: cmd and val
# cmd:
HELM	= 1 # val = -90 to +90, negative:port, positive:starboard, zero:amidships
THROTTLE= 2 # val = -90 to +90, negative:astern, positive:ahead, zero:stop

minimum_skate_time = .1
serialOpenSettleTime = .5  # why?
serialSendSettleTime = .2  # .9 fails  timeout on the read side?
prevSerialSend = 0.0

# global constants, initialized one-time within skate_process
scomm = False	# instantiation of Serial object

# global variables
helm = 0
throttle = 0
heading = 0
roll = 0

# buffer to receive data from sensor
ahrs = AHRS()

# used internally for execution control
donut_time = 0.0
heading_time = 0.0
eta = 0.0
pilot_firstime = True

# x,y positions, in cm
donut = [0,0]
cbase = [0,0]  # center of wheelbase
gate = [0,0]   # start and end position

# navigation data
plan = []
route = []
routendx = -1
leg = {}
captains_log = []  # used for dead reckoning

# calibration constants and variables
FIGURE_8_HALF_TIME = 5
MAG_CALIBRATION_MAX_TIME = 20
FULLY_CALIBRATED = 3

gyro_calibrated = 0
mag_calibrated = 0
calibration_started = 0
maneuver_started = 0

# global shared inter-process memory
gmem_timestamp = None
gmem_positions = None

time_photo = 0.0
time_helm = 0.0

def kill(msg):
	jlog.info(f'kill: {msg}')
	gmem_timestamp[TIME_KILLED] = time.time()

# ---- comm -----

def sendCommandToSk8(cmd, val):
	global helm, throttle, prevSerialSend
	value = val
	settleTime = serialSendSettleTime - (time.time() - prevSerialSend)
	if settleTime > 0:
		time.sleep(settleTime)

	if cmd == HELM:
		helm = value
		if abs(helm) > 90:
			kill(f'bad helm request {helm}')
		value = specs.applyHelmBias(helm)
	if cmd == THROTTLE:
		throttle = value
		if abs(throttle) > 90:
			kill(f'bad throttle request {throttle}')

	s = f'{cmd}\t{value}\n' 
	if not scomm:
		jlog.info(f'command not sent, no serial')
	else:
		scomm.write(bytes(s, 'utf-8'))
		jlog.debug(f'command sent to sk8: {s.strip()}')
	prevSerialSend = time.time()

def testSerialAhrs():
	jlog.debug(f'begin testSerialAhrs')
	serialreadsettletime = 0
	num = 0  # we typically receive 42 messages per second
	for i in range(50):
		jlog.debug(f'in_waiting: {scomm.in_waiting}')
		scomm.reset_input_buffer()

		b = scomm.readline()	# serial read to \n or timeout, whichever comes first
		jlog.debug(f'num:{num} len:{len(b)}')

		s = b.decode("utf-8")	# to tab-separated string
		jlog.debug(f's: {s}')

		lst = s.split()		# parse into global struct
		jlog.debug(f'count: {len(lst)}')

		time.sleep(serialreadsettletime)
		num += 1
	
	jlog.debug(f'end testSerialAhrs')

def getAhrsFromSk8():
	global heading, roll

	lst = [1,2]
	if len(lst) != 7:
		scomm.reset_input_buffer() # make sure we get the latest message
		b = scomm.readline()	# serial read to \n or timeout, whichever comes first
		s = b.decode("utf-8")	# to tab-separated string
		lst = s.split()		# parse into global struct
		if len(lst) != 7:
			jlog.info(f'incomplete serial ahrs message ignored {len(lst)}')
		return

	ahrs.heading	= float( lst[0])
	ahrs.roll	= float( lst[1])
	ahrs.pitch	= float( lst[2])
	ahrs.sys	= int( lst[3])
	ahrs.gyro	= int( lst[4])
	ahrs.accel	= int( lst[5])
	ahrs.mag	= int( lst[6])
	jlog.debug(f'lenstr:{len(b)}, lenlst:{len(lst)}, heading:{ahrs.heading:.2f}, roll:{ahrs.roll}, gyro:{ahrs.gyro}, mag:{ahrs.mag}')

	# the BRO055 does NOT adjust for magnetic declination, so we do that here
	adjheading = ahrs.heading + args.declination
	if adjheading < 0:
		adjheading = (360 - adjheading)

	# on new heading
	if not int(heading) == int(adjheading):
		heading = int(adjheading)
		gmem_positions[SKATE_HEADING] = heading
		gmem_timestamp[TIME_HEADING] = time.time()

	# on new roll
	if not int(roll) == int(ahrs.roll):
		roll = int(ahrs.roll)
		gmem_positions[SKATE_ROLL] = roll
		gmem_timestamp[TIME_ROLL] = time.time()

def connectSerial():
	global scomm
	scomm = serial.Serial(port=args.port, baudrate=args.baud, timeout=args.serialtimeout)
	# scomm is a port object with api: write, readline, in_waiting, etc

	time.sleep(serialOpenSettleTime)  # why?
	jlog.debug(f'serial port is {"open" if scomm.isOpen() else "NOT open"}')
	return scomm

# ---- calibration -----

def calibrate():
	global gyro_calibrated, mag_calibrated
	getAhrsFromSk8()
	gyro_calibrated = calibrateGyro()
	mag_calibrated = calibrateMag()

def calibrateMag():
	global calibration_started, maneuver_started
	if ahrs.mag >= FULLY_CALIBRATED:
		sendCommandToSk8( THROTTLE, 0)
		sendCommandToSk8( HELM, 0)
		return True

	if ((calibration_started > 0) and (time.time() - calibration_started) > MAG_CALIBRATION_MAX_TIME):
		sendCommandToSk8( THROTTLE, 0)
		sendCommandToSk8( HELM, 0)
		raise Exception('magnometer calibration timed out')

	if calibration_started <= 0:
		calibration_started = time.time()
		maneuver_started = calibration_started
		sendCommandToSk8( HELM, 90)
		sendCommandToSk8( THROTTLE, 23)
	else:
		if time.time() - maneuver_started > FIGURE_8_HALF_TIME:
			newhelm = (0 - helm)  # reverse
			sendCommandToSk8( HELM, newhelm)
			maneuver_started = time.time()

def calibrateGyro():
	if ahrs.gyro >= 3:
		return True
	nudgeHelm()
	return False

# ---- process target -----

def skate_main(timestamp, positions):
	global scomm, gmem_timestamp, gmem_positions
	try:
		jlog.setup('skate', args.verbose, args.quiet)
		jlog.info(f'starting process id: {os.getpid()}, serialSendSettleTime:{serialSendSettleTime}')
		gmem_timestamp = timestamp
		gmem_positions = positions
		signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore KeyboardInterrupt
		scomm = connectSerial()
		if not scomm:
			raise Exception('serial port connection failed')
		jlog.info(f'serial port connected')

		#testSerialAhrs()
		#kill('serial test ended')
		#raise Exception('normal end of test')
		getAhrsFromSk8()

		# calibration
		if not args.nocal:
			while True:
				if (ahrs.gyro and ahrs.mag):
					jlog.info(f'calibrated \a')
					break
				if gmem_timestamp[TIME_KILLED]:
					jlog.info(f'calibration killed')
					break
				jlog.info(f'calibrating gyro:{ahrs.gyro}, mag:{ahrs.mag}')
				time.sleep(.5)
				getAhrsFromSk8()

		# wait for first photo, then setup arena
		while not gmem_timestamp[TIME_PHOTO] and not gmem_timestamp[TIME_KILLED]:
			time.sleep(.1)

		configArena()

		# wait here until everybody ready
		jlog.info('ready')
		gmem_timestamp[TIME_SKATE_READY] = time.time()
		while not gmem_timestamp[TIME_READY] and not gmem_timestamp[TIME_KILLED]:
			time.sleep(.1)

		# main loop
		while True:
			if gmem_timestamp[TIME_KILLED]:
				jlog.info(f'stopping main loop to kill')
				break

			getAhrsFromSk8()

			rc = pilot()
			if not rc:
				jlog.info(f'pilot returned False')
				break
			jlog.info(f'loop cbase:{cbase}, routendx:{routendx}, heading:{heading}')

		kill("drop out of main loop")

	except KeyboardInterrupt:
		jlog.error('never happen')

	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		jlog.error(f'exception: {ex}, {exc_type}, {fname}, {exc_tb.tb_lineno}')
		if args.verbose:
			jlog.error(traceback.format_exc())
		kill('exception')
	finally:
		try:
			sendCommandToSk8( THROTTLE, 0)
			sendCommandToSk8( HELM, 0)
			if scomm and scomm.isOpen():
				scomm.close()
		except Exception as ex:
			jlog.error(f'shutdown exception: {ex}')
		jlog.info(f'main exit')

# ----------------------------------------
#    pilot and navigator
# ----------------------------------------

def onRoll():
	global helm
	error = heel - roll
	helm_adj = pid( error)
	helm += helm_adj

def calcCenterWheelbase(donut):
	theta = nav.thetaFromHeading( heading + helm)
	cbase = nav.pointFromTheta( donut, theta, specs.helm_length)
	# we should also apply the helm_offset and roll_y_offset
	return cbase

#def px2cm(pt):
#	return [(pt[0] - 300) * cmPerPx, (pt[1] - 300) * cmPerPx]

#def cm2px(pt):
#	return [int((pt[0] * pxPerCm + 300)), int((pt[1] * pxPerCm + 300))]

def configArena():
	global cones, donut, cbase, gate, plan, route, routendx
	# unwind shared memory into cones
	cones = []
	numcones = gmem_positions[NUM_CONES]
	pos = CONE1_X
	for i in range(numcones):
		pt = [gmem_positions[pos], gmem_positions[pos+1]]
		cone = specs.awacs2skate(pt)
		cones.append(cone)
		pos += 2
	#cones = list(reversed(cones))

	donut = specs.awacs2skate([gmem_positions[DONUT_X], gmem_positions[DONUT_Y]])
	cbase = calcCenterWheelbase(donut)
	gate = cbase

	jlog.debug(f'cones: {cones}')
	jlog.debug(f'donut: {donut}')
	jlog.debug(f'cbase: {cbase}')
	jlog.debug(f'gate: {gate}')

	order, sides = planRoute(cones)
	order = [0,1]
	sides = ['cw', 'cw']
	jlog.debug(f'order: {order}, sides: {sides}')

	plan = calcPlan(cones, order, sides)
	jlog.debug(f'plan: {plan}')

	route = plotRoute(plan)
	routendx = -1
	jlog.debug(f'route: {route}')

	# first log entry
	log( cbase, time.time(), 0, 0)

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
	for i in range(len(cones)):
		plan.append({
			'order':order[i], 
			'center':cones[i], 
			'rdir':sides[i], 
		})
	plan = sorted(plan, key=lambda cone: cone['order'])

	# add entry and exit points to each cone
	r = specs.turning_radius
	localgate = { 'center': gate }
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
	prevexit = gate
	for i in range(0,len(plan)):
		cone = plan[i]

		bearing = nav.headingOfLine(prevexit, cone['entry'])
	
		route.append({
			'shape': 'line',
			'from': prevexit,
			'to': cone['entry'],
			'bearing': bearing,
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
	jlog.debug(f'back to starting gate: {prevexit}, {gate}')
	bearing = nav.headingOfLine(prevexit, gate)
	route.append({
		'shape': 'line',
		'from': prevexit,
		'to': gate,
		'bearing': bearing,
	})
	return route

def nextLeg():
	global routendx, leg
	routendx += 1
	leg = route[routendx]

	jlog.info(f'leg {routendx}: {leg}')

	if leg['shape'] == 'arc':
		if leg['rdir'] == 'cw':
			sendCommandToSk8(HELM, +90)
		elif ['rdir'] == 'ccw':
			sendCommandToSk8(HELM, -90)
	elif leg['shape'] == 'line':
		sendCommandToSk8(HELM, 0)

def isOnMark(point1, point2):
	n = nav.lengthOfLine(point1, point2)
	return n < 3

def helmpid(err):
	jlog.debug('helm pid')
	Kp = .6
	adj = Kp * err
	return 0 # adj

def log(pos, timestamp, heading, speed):
	ndx = len(captains_log)
	if ndx > 0:
		ndx = len(captains_log) - 1
		captains_log[ndx]['heading'] = heading
		captains_log[ndx]['speed'] = speed
	captains_log.append({'startpos': pos, 'starttime':timestamp, 'heading':heading, 'speed':speed})

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
	global donut_time, pilot_firstime, helm, time_photo, time_helm, cbase
	jlog.debug(f'in pilot')
	position_changed = False

	# first time
	if routendx == -1:
		sendCommandToSk8(THROTTLE, 23)
		nextLeg()

	# on heading change
	if gmem_timestamp[TIME_HEADING] > time_helm:
		time_helm = time.time()

		# calc current position using previous position and starttime, but current heading
		crs = captains_log[len(captains_log)-1]
		elapsed = time_helm - crs['starttime']
		distance = elapsed * specs.speed 
		cbase = nav.reckonLine(cbase, heading, distance)
		position_changed = True

		# log this moment just before helm change
		log( cbase, time_helm, heading, specs.speed)

	# on photo
	#if gmem_timestamp[TIME_PHOTO] > time_photo:
	#	time_photo = gmem_timestamp[TIME_PHOTO]
	#	donut = specs.awacs2skate([gmem_positions[DONUT_X], gmem_positions[DONUT_Y]])
	#	donutcbase = calcCenterWheelbase(donut)

	#	orgcbase = cbase

	#	course = readLogByDate(time_photo)
	#	vector = course['startpos'] - donutcbase
	#	cbase = cbase + vector
	#	position_changed = True

	#	jlog.info(f'orgcbase:{orgcbase}, donut:{donut}, donutcbase:{donutcbase}, vector:{vector}, cbase:{cbase}')

	# on rounding mark
	if isOnMark(cbase, leg['to']):
		if routendx >= len(route):  # journey's end
			sendCommandToSk8(THROTTLE, 0)
			sendCommandToSk8(HELM, 0)
			return False
		else:
			nextLeg()

	# keep skate on course
	if leg['shape'] == 'line':
		# recalc bearing based on new position
		error = leg['bearing'] - heading
		helm_adj = helmpid( error)
		jlog.debug(f'adj:{helm_adj}, err:{error}, bearing:{leg["bearing"]}, heading:{heading}')
		sendCommandToSk8(HELM, helm_adj)
	elif leg['shape'] == 'arc':
		# ? what can we do ?
		pass
	
	if position_changed:
		pt = specs.skate2gcs(cbase)
		jlog.info(f'cbase:{cbase}, pt:{pt}')
		gmem_positions[SKATE_X] = pt[0]
		gmem_positions[SKATE_Y] = pt[1]
	return True

def nudgeHelm():
	sendCommandToSk8( HELM, 5)
	time.sleep(.1)
	sendCommandToSk8( HELM, 0)

