'''
skate.py

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
roles:
	captain - design route from choice of patterns 
	navigator - dead reckon position, adjust course
	pilot - keep the vehicle on course
brain parts:
	


add piloting to skate.py
	for dev and test
		use constants for cones and route
		see hippoc for how this variables are designed

	pull in specs and math
		sk8minimath.py is mostly from arduino/sk8.ino, and currently contains specs, not math 
		see: ~/webapps/robots/robots/autonomy/nav.py - library of trigonometry used in navigation
		write math to adjust throttle depending on roll

	separate throttle and helm commands
		change class PILOT to class CMD
		change PILOT structure in sk8mini.h and skate.py
	
	add onRoll: adjust right-throttle
	
	event-driven
		On roll, adjust throttle
		On heading, dead reckon
		On time elapsed, 
		On position, pilot 
		On cone rounded, navigate
	
	finish figure 8 pattern for calibration, with right throttle adjustment


add navigation
	pull in stuff from hippoc.py

	dead reckoning
		keep list of recent commands
		with each new command, calc new position by adding previous command

cones[] - 2D array of x,y points
plan - cones, order, sides
route 

placeCones() -> cones[] a 2D array of x,y points within the arena
planRoute(cones) -> order, sides
	input - cones array
	output - order: array of cone numbers, sides: array of strings, 'ccw' or 'cw'


plan = calcPlan(cones, order, sides)
	output plan is list of dicts, sorted by order
		each dict 
			order
			center
			rdir
			entry
			exit

route = plotRoute(plan)
		each dict
			shape line
			from point
			to point
			bearing
		or
			shape arc
			from point
			to point
			center point
			rdir rotation direction cw or ccw


list of [conenum, side] in order
for execution, add entry and exit points


save center from donut
	special op
	save to disk, then shutdown
	mode, like sim

throttle adjustment is relative to roll, not helm
	therefore, perhaps we should go back to separate commands
	if doing async, we need events
		onRoll - adjust throttle depending on roll
		onHeading - adjust helm to keep course bearing and/or turn radius
		onPosition - override dead-reckoning position
----------------------

Pilot
        Run through a stack of legs
        If heading not = bearing, helm
        Else helm 0
        If dest = position, next leg
        If time we'll past eta, kill
        When starting leg, calc eta
        Add start, stop to leg
        Stop is eta until completed
        If next dest reached
                Bump to next leg

Navigate
        Stack of legs
        Stack of ahrs
        When stack full, save and clear

        On donut
                Set center
                        Three offsets: 0, 90, -90

-------------

Take photos
        calc pixel to cm, conversion

Do all positions in cm, With 0,0 at the arena center

Go to point (two legs: 1 arc, 1 line)
        Calc two angles
        Choose the smaller
        Full arc
        Line to dest

On roll
        Dead reckon

---------------

run exercises
        1. Count rpm at each speed setting
        2. Measure actual distance and time 
                Get photo save working
                Get pilot commands working
        3.  Math circum of turning radius,
                throttle, throttle left, throttle right
'''

import signal
import os
import serial
import time

import jlog
from smem import *
import sk8mini_specs

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

# global constants, set by gcs.py argparse before skate_process is started
verbose	= True
quiet	= False
nocal	= False
port	= '/dev/ttyUSB0'  # serial port for dongle
baud	= 115200
serialtimeout = 3
serialminbytes = 10
declination = -1.11 # from magnetic-declination.com depending on lat-lon

minimum_skate_time = .1
serialOpenSettleTime = .5  # why?
serialSendSettleTime = .2  # .9 fails  timeout on the read side?
prevSerialSend = 0.0

# global constants, initialized one-time within skate_process
scomm = False	# instantiation of Serial object

# global variables
helm = 0
throttle = 0
ahrs = AHRS()
donut_time = 0.0
pilot_firstime = True
eta = 0.0
bearing = 0

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

# ---- comm -----

def sendCommandToSk8(cmd, val):
	global helm, throttle, prevSerialSend
	settleTime = serialSendSettleTime - (time.time() - prevSerialSend)
	if settleTime > 0:
		time.sleep(settleTime)

	if cmd == HELM:
		helm = val
	if cmd == THROTTLE:
		throttle = val

	s = f'{cmd}\t{val}\n' 
	if not scomm:
		jlog.info(f'skate: command not sent, no serial')
	else:
		scomm.write(bytes(s, 'utf-8'))
		jlog.debug(f'skate: command sent to sk8: {s.strip()}')
	prevSerialSend = time.time()

def getAhrsFromSk8():
	global gmem_timestamp, gmem_positions
	if scomm.in_waiting < serialminbytes:   # number of bytes in the receive buffer
		# sk8.ino sends data only when it changes - NOT
		return False

	b = scomm.readline()	# serial read to \n or timeout, whichever comes first
	if len(b) <= 0:
		jlog.debug(f'skate: serial read returned len 0')
		return False

	s = b.decode("utf-8")	# to tab-separated string
	lst = s.split()		# parse into global struct

	if len(lst) < 7:
		jlog.error(f'skate: serial read incomplete, {len(lst)}, {len(b)}, {b}')
		return False

	# temp variables
	heading	= float( lst[0])
	roll	= float( lst[1])

	# the BRO055 does NOT adjust for magnetic declination, so we do that here
	heading += declination
	if heading < 0:
		heading = (360 - ahrs.heading)

	if not int(ahrs.heading) == int(heading):
		ahrs.heading = heading
		gmem_positions[SKATE_HEADING] = int(ahrs.heading)
		gmem_timestamp[TIME_HEADING] = time.time()

	if not int(ahrs.roll) == int(float( lst[1])):
		ahrs.roll = roll
		gmem_positions[SKATE_ROLL] = int(ahrs.roll)
		gmem_timestamp[TIME_ROLL] = time.time()

	#ahrs.heading	= float( lst[0])
	#ahrs.roll	= float( lst[1])
	ahrs.pitch	= float( lst[2])
	ahrs.sys	= int( lst[3])
	ahrs.gyro	= int( lst[4])
	ahrs.accel	= int( lst[5])
	ahrs.mag	= int( lst[6])

	jlog.debug(f'skate: heading:{ahrs.heading:.2f}, roll:{ahrs.roll}, gyro:{ahrs.gyro}, mag:{ahrs.mag}')
	return True

def connectSerial():
	global scomm
	scomm = serial.Serial(port=port, baudrate=baud, timeout=serialtimeout)
	# scomm returns a port object with api: write, readline, in_waiting, etc

	jlog.debug(f'serial port is open? {scomm.isOpen()}')
	time.sleep(serialOpenSettleTime)  # why?
	jlog.debug(f'serial port is open? {scomm.isOpen()}')
	return scomm

def testSerial():
	# test the connection through dongle to the sk8
	ahrs_updated = getAhrsFromSk8()
	if not ahrs_updated:
		return False		
	return scomm

# ---- calibration -----

def calibrate():
	global gyro_calibrated, mag_calibrated
	ahrs_updated = getAhrsFromSk8()
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
		jlog.setup(verbose, quiet)
		jlog.debug(f'skate: starting process id: {os.getpid()}')
		gmem_timestamp = timestamp
		gmem_positions = positions
		signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore KeyboardInterrupt
		scomm = connectSerial()
		if not scomm:
			raise Exception('serial port connection failed')
		jlog.debug(f'skate: serial port connected')
			
		while not nocal:
			if timestamp[TIME_KILLED]:
				jlog.info(f'skate: stopping due to kill')
				break
			if gyro_calibrated and mag_calibrated:
				break
			calibrate()

		# wait for first photo, then setup arena
		while not timestamp[TIME_PHOTO] and not timestamp[TIME_KILLED]:
			time.sleep(.1)
			placeCones()

		# wait here until everybody ready
		jlog.info('skate: ready')
		timestamp[TIME_SKATE_READY] = time.time()
		while not timestamp[TIME_READY] and not timestamp[TIME_KILLED]:
			time.sleep(.1)

		# main loop
		while True:
			if timestamp[TIME_KILLED]:
				jlog.info(f'skate: stopping due to kill')
				break
			rc = pilot()
			if not rc:
				break
			navigate()

		jlog.debug("skate: drop out of main loop")

	except KeyboardInterrupt:
		jlog.error('never happen')

	except Exception as ex:
		jlog.error(f'skate: exception: {ex}')
		timestamp[TIME_KILLED] = time.time()
	try:
		sendCommandToSk8( THROTTLE, 0)
		sendCommandToSk8( HELM, 0)
		scomm.close()
	except Exception as ex:
		jlog.error(f'skate: shutdown exception: {ex}')

	jlog.info(f'skate: main exit')

# ---- arena config -----

wArena = 600
hArena = 600
orientationArena = 0  # heading of up
centerArena = [0,0]
xArenaMin = centerArena[0] - int(wArena/2)
xArenaMax = centerArena[0] + int(wArena/2)
yArenaMin = centerArena[1] - int(hArena/2)
yArenaMax = centerArena[1] + int(hArena/2)

vcones = {
	'square': [
		[ -200, +200],	# NW 
		[ +200, +200],	# NE
		[ +200, -200],	# SE
		[ -200, -200]	# SW
	],
	'ironcross': [
		[    0, +200],	# N
		[ +200, +200],	# E
		[    0, -200],	# S
		[ -200, -200] 	# W
	]
}

def configArena():
	#gate = starting donut
	#start position, start heading
	
	if args.vcones:
		placeVirtualCones(args.vcones)

def placeVirtualCones(vconename):
	vcenter = False # has + appended to vconename 
	cones = vcones[vconename]	
	if vcenter:
		cones.append(centerArena)
	numcones = len(cones)

def placeCones():
	pass
	

def isArenaReady():
	#has cones?
	#has gate?
	pass



# ----  gallery of patterns ----------

CW	= 1 # enter on the left
CCW	= 2 # enter on the right

patterns = {
	'straightLine': [
		[0, CW],
		[1, CW],
	]
}

plan = [ 
  	{ 'legnum': 1, 'conenum':1, 'rdir': CW},
  	{ 'legnum': 2, 'conenum':3, 'rdir':CCW},
  	{ 'legnum': 3, 'conenum':1, 'rdir': CW},
  	{ 'legnum': 4, 'conenum':3, 'rdir':CCW},
  	{ 'legnum': 5, 'conenum':1, 'rdir': CW},
  	{ 'legnum': 6, 'conenum':3, 'rdir':CCW},
  	{ 'legnum': 6, 'conenum':1, 'rdir': CW},
  	{ 'legnum': 8, 'conenum':3, 'rdir':CCW},
  	{ 'legnum': 9, 'conenum':1, 'rdir': CW},
  	{ 'legnum':10, 'conenum':3, 'rdir':CCW} 
]

# ---- captain -----

def choosePattern():
	return 'straightLine'

# ---- navigator -----

def calcPlan(plan):
	# calc entry and exit points for each cone
	r = spec.turningradius
	gate = { 'center': (spec.gatex,spec.gatey) }

	for i in range(len(plan)):
		cone = plan[i]
		prevcone = gate if i <= 0 else plan[i-1]
		nextcone = gate if i+1 >= len(plan) else plan[i+1] 

		# entry point
		# draw line AB from the previous cone to the current cone
		A = prevcone['center']
		B = cone['center']

		# draw line LR perpendicular to AB, intersecting the cone center and the turning circle 
		L, R = nav.linePerpendicular(A, B, r)

		# this gives us two choices for entry point: Left and Right
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
	

#route = [ 
#  	[1, CW],
#  	[3, CCW],
#  	[1, CW],
#  	[3, CCW],
#  	[1, CW],
#  	[3, CCW],
#  	[1, CW],
#  	[3, CCW],
#  	[1, CW],
#	[3, CCW]
#]
#numlegs = len(route)
#
#def choosePattern():
#	nextPattern = 'barrelrace'
#
#	legs = False
#	if nextPattern == 'barrelrace':
#		# choose 3 cones at random
#		patternSize = 3
#		coneorder = random.sample(range(0, numcones), patternSize)
#		legs = [None] * patternSize
#		for i in range(len(legs)):
#			legs[i].conenum = coneorder[i]
#			legs[i].rdir = random.randint(0,1)
#
#		plan.append({
#			'order':order[i], 
#			'center':cones[i], 
#			'rdir':sides[i], 
#	return legs

# ---- pilot -----

CW	= 1
CCW	= 2

class Leg:
	order	= 0,
	center	= [0,0]
	rdir	= CW
	entry	= [0,0]
	exit	= [0,0]

max_legs = 100  # we work with a fixed size route
num_legs = 0
current_leg = 0
route = [None] * max_legs

def appendLeg(leg):
	route[num_legs] = leg
	num_legs += 1

def cycleRoute():
	# save used legs to disk
	# remove used legs from route
	pass

def pilot():
	global donut_time, pilot_firstime, eta, gmem_timestamp, bearing
	#jlog.debug(f'skate: pilot')

		
	#sendCommandToSk8(THROTTLE, 23)
	#sendCommandToSk8(HELM, -40)
	#sendCommandToSk8(HELM, 40)
	#sendCommandToSk8(HELM, 0)
	#return False # break main loop


	if pilot_firstime:
		sendCommandToSk8(THROTTLE, 23)
		sendCommandToSk8(HELM, 90) # -18)
		eta = time.time() + 7
		bearing = 0
		pilot_firstime = False
	else:
		if time.time() > eta:
			return False

	return True

	#if gmem_timestamp[TIME_ROLL]:
	#	adjustHelm()

	if True: #gmem_timestamp[TIME_DONUT] > donut_time:
		#donut_time = gmem_timestamp[TIME_DONUT]
		donut_time = gmem_timestamp[TIME_PHOTO]
		detectPosition()
	else:
		reckonPosition()

	if isLegComplete():
		nextLeg()
	else:
		tweakHelm()

	#if no route:
	#	return

def nudgeHelm():
	sendCommandToSk8( HELM, 5)
	time.sleep(.1)
	sendCommandToSk8( HELM, 0)

def adjustHelm():
	global helm
	err = ahrs.heading - bearing
	if err < 0:
		adj = -10
	if err > 0:
		adj = +10
	helm += adj
	sendCommandToSk8(HELM, adj)

def pause():
	pass

def figure8():
	pass

# ---- navigator -----
def navigate():
	return

'''	
iniate
	choosePattern
	add to route
	set legnum to 0

pilot
	if not moving
		set throttle
	compare position
	if position reached:
		legnum += 1
	if line:
		compare heading to bearing
		if off:
			set helm
	if arc:
		compare time to eta
		if past:
			legnum += 1
		


def navigate():
	jlog.debug(f'skate: navigate')
	if route almost finished or no route at all:
		legs = choosePattern()
		add legs to route
		current leg = 

'''
