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
import matplotlib
import matplotlib.pyplot as plt
import math

import jlog
from smem import *
import specs
import nav


# buffer to receive data from sensor
class AHRS:
	heading	= 9999.0
	roll	= 0.0
	pitch	= 0.0
	sys	= 0
	gyro	= 0
	accel	= 0
	mag	= 0
ahrs = AHRS()

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

# used internally for execution control
donut_time = 0.0
heading_time = 0.0
eta = 0.0
autopilot = True

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

# global shared inter-process memory
gmem_timestamp = None
gmem_positions = None

time_photo = 0.0
time_helm = 0.0

args = None   # command-line arguments
def setupArgParser(parser):
	parser.add_argument('--port'           ,default='/dev/ttyUSB0'        ,help='serial port'                      )
	parser.add_argument('--baud'           ,default=115200    ,type=int   ,help='serial baud rate'                 )
	parser.add_argument('--serialtimeout'  ,default=3         ,type=int   ,help='serial timeout'                   )
	parser.add_argument('--serialminbytes' ,default=10        ,type=int   ,help='serial minimum bytes before read' )
	parser.add_argument('--declination'    ,default=-1.11     ,type=float ,help='# from magnetic-declination.com'  )
	parser.add_argument('--nocal'          ,action='store_true'           ,help='suppress calibration'             )
	parser.add_argument('--helmbias'       ,default=specs.helm_bias,type=int,help='helm value giving straight line'  )

# ----------------------------------------
#    comm
# ----------------------------------------

def connectSerial():
	global scomm
	try:
		scomm = serial.Serial(port=args.port, baudrate=args.baud, timeout=args.serialtimeout)
		# scomm is a port object with api: write, readline, in_waiting, etc
	except:
		return False

	time.sleep(serialOpenSettleTime)  # why?
	jlog.debug(f'serial port is {"open" if scomm.isOpen() else "NOT open"}')
	return scomm

def applyHelmBias(helm): 
	return max(-90, helm + args.helmbias)

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
		value = applyHelmBias(helm)
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

	# note: future use, awacs may use heading and roll to write labels
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

# ----------------------------------------
#    process target
# ----------------------------------------

time_photo_max_delay = 3.0 # seconds
skate_paused = False

def kill(msg):
	gmem_timestamp[TIME_KILLED] = time.time()
	jlog.info(f'kill: {msg}')

def isKilled():
	return (gmem_timestamp[TIME_KILLED] > 0)
	
def hasPhoto():
	return (gmem_timestamp[TIME_PHOTO] > time_photo)

def isPhotoLate():
	return (gmem_timestamp[TIME_PHOTO] <= time_photo) and ((time.time() - time_photo) > time_photo_max_delay)

def isSkatePaused():
	return skate_paused

def pause():
	global skate_paused
	skate_paused = True

def unpause():
	global skate_paused
	skate_paused = False 

def skate_main(timestamp, positions):
	global scomm, gmem_timestamp, gmem_positions
	try:
		jlog.setup('skate', args.verbose, args.quiet)
		jlog.info(f'starting process id: {os.getpid()}, serialSendSettleTime:{serialSendSettleTime}')
		gmem_timestamp = timestamp
		gmem_positions = positions
		signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore KeyboardInterrupt

		# serial port
		scomm = connectSerial()
		if not scomm:
			kill(f'serial port {args.port} connection failed')
			return

		jlog.info(f'serial port connected')
		getAhrsFromSk8()
		jlog.info(f'AHRS connected')

		# setup loop
		calibrated	= False
		arena_ready	= False
		ui_ready	= False
		user_go	= False
		while True:
			if isKilled():
				jlog.info(f'stopping setup loop due to kill')
				break

			if not calibrated:
				jlog.info('calibrating...')
				getAhrsFromSk8()
				if ahrs.mag >= 3 and ahrs.gyro >= 3:
					jlog.info('ahrs calibrated')
					calibrated = True

			elif not arena_ready:
				if gmem_timestamp[TIME_PHOTO]:
					configArena()
					jlog.info('arena configured')
					arena_ready = True

			elif not ui_ready:
					startUI()
					refreshUI()
					ui_ready = True
					jlog.debug('click g to go')

			elif not user_go:
				getAhrsFromSk8()
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

			if isPhotoLate():
				pause()

			getAhrsFromSk8()
			refreshUI()
			if ui.eventkey:
				key = respondToKeyboard()

			if hasPhoto():
				jlog.debug(f'has photo')
				if isSkatePaused():
					unpause()
				pilot()	

			jlog.debug(f'loop cbase:{cbase}, routendx:{routendx}, heading:{heading}')

		kill("drop out of main loop")

	except KeyboardInterrupt:
		jlog.error('never happen')

#	except Exception as ex:
#		exc_type, exc_obj, exc_tb = sys.exc_info()
#		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
#		jlog.error(f'exception: {ex}, {exc_type}, {fname}, {exc_tb.tb_lineno}')
#		if args.verbose:
#			jlog.error(traceback.format_exc())
#		kill('exception')

	finally:
		try:
			kill('finally')
			if scomm and scomm.isOpen():
				sendCommandToSk8( THROTTLE, 0)
				sendCommandToSk8( HELM, 0)
				scomm.close()
		except Exception as ex:
			jlog.error(f'shutdown exception: {ex}')
	jlog.info(f'main exit')

# ----------------------------------------
#    navigator
# ----------------------------------------

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
	cones = list(reversed(cones))

	donut = specs.awacs2skate([gmem_positions[DONUT_X], gmem_positions[DONUT_Y]])
	cbase = calcCenterWheelbase(donut)
	ui.cbaseChanged = True
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
	for i in range(len(order)):
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

		route.append({
			'shape': 'line',
			'from': prevexit,
			'to': cone['entry'],
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
	route.append({
		'shape': 'line',
		'from': prevexit,
		'to': gate,
	})
	return route

# ----------------------------------------
#    pilot
# ----------------------------------------

def onRoll():
	global helm
	error = heel - roll
	helm_adj = pid( error)
	helm += helm_adj

def nextLeg():
	global routendx, leg
	routendx += 1
	leg = route[routendx]

	jlog.info(f'next leg {routendx}: {leg}')

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

# pid control of steering
# see https://docs.google.com/spreadsheets/d/1oKY4mz-0K-BwVNZ7Tu-k9PsOq_LeORR270-ICXyz-Rw/edit#gid=0
def helmpid(err):
	jlog.debug('helm pid')
	Kp = 2
	adj = Kp * err
	adj = max(-90,min(90,adj))
	return adj

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
	global donut_time, helm, time_photo, time_helm, cbase
	jlog.debug(f'in pilot')
	position_changed = False

	tm = time.time()

	# first time
	if routendx == -1:
		sendCommandToSk8(THROTTLE, 23)
		nextLeg()

	# get new position
	if hasPhoto():	
		time_photo = gmem_timestamp[TIME_PHOTO]
		donut = specs.awacs2skate([gmem_positions[DONUT_X], gmem_positions[DONUT_Y]])
		prevcbase = cbase
		cbase = calcCenterWheelbase(donut)
		ui.cbaseChanged = True

	# log this moment just before helm change
	log( cbase, time_helm, heading, specs.speed)

	if not autopilot:
		return

	# on rounding mark
	if isOnMark(cbase, leg['to']):
		if routendx >= len(route):  # journey's end
			sendCommandToSk8(THROTTLE, 0)
			sendCommandToSk8(HELM, 0)
			return False
		else:
			nextLeg()

	# stay on course
	if leg['shape'] == 'line':
		bearing = nav.headingOfLine(cbase, leg['to'])
		error = bearing - heading
		if error > 180:
			error -= 360
		if error < -180:
			error += 360
		helm_adj = helmpid( error)
		jlog.info(f'pilot: new_helm:{helm_adj}, err:{error}, bearing:{bearing}, heading:{heading}')
		sendCommandToSk8(HELM, helm_adj)

	elif leg['shape'] == 'arc':
		jlog.info(f'pilot: arc, heading:{heading}, cbase:{cbase}, leg-to:{leg["to"]}')

def nudgeHelm():
	sendCommandToSk8( HELM, 5)
	time.sleep(.1)
	sendCommandToSk8( HELM, 0)

# ----------------------------------------
#    UI
# ----------------------------------------

# global constants
fps = 20
ui_delay = 1/fps  # .05
ui_pause = .001

fname = 'arena_%timestamp%.png'

# artists
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
	refresh_time = 0.0
	eventkey = False
ui = UI()

def onpress(event):
	ui.eventkey = event.key

def startUI():
	# setup artists
	ui.fig, ui.ax = plt.subplots()
	plt.xlim(-132,+132)
	plt.ylim(-132,+132)
	plt.autoscale(False)  # if True it will adapt x,ylim to the data
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	ui.ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize
	ui.fig.canvas.mpl_connect('key_press_event', onpress) # keypress event handler

	# cones
	for pt in cones:
		circ = plt.Circle(pt, 10, color='y')
		ui.ax.add_artist(circ)
		ui.cones.append(circ)
		t = plt.text(pt[0], pt[1], str(len(ui.cones)), fontsize='12', ha='center', va='center', color='black')
		ui.conetexts.append(t)
		ui.conesChanged = True
		
	# route legs
	for leg in route:
		if leg['shape'] == 'line':
			A = (leg['from'])
			B = (leg['to'])
			xd,yd = np.transpose([A,B]); 
			linesegs = plt.plot(xd,yd, color='black', lw=1) # returns list of line2D objects
			ui.legs.append(linesegs[0])
		elif leg['shape'] == 'arc':
			A = (leg['from'])
			B = (leg['to'])
			C = (leg['center'])
			tA,_ = nav.thetaFromPoint(A, C)
			tB,_ = nav.thetaFromPoint(B, C)
			rdir = leg['rdir']
			r = 23
			t1 = tA
			t2 = tB
			if rdir == 'cw': 
				t1 = tB
				t2 = tA
				if t1 == t2:
					t2 -= .001
			arc = matplotlib.patches.Arc(C, r*2, r*2, 0, math.degrees(t1), math.degrees(t2), color='black')
			ui.ax.add_patch(arc)
			ui.legs.append(arc)
		ui.routeChanged = True

	# skate
	ui.skateline = ui.ax.scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])
	ui.cbaseChanged = True

def refreshUI():
	jlog.debug(f'refresuUI, {time.time()}, {ui.refresh_time}')
	if time.time() - ui.refresh_time >= ui_delay:
		jlog.debug(f'inside refresuUI, {ui.conesChanged}, {ui.routeChanged}, {ui.cbaseChanged}')
		if ui.conesChanged:
			i = 0
			for i in range(len(ui.cones)):
				ui.cones[i].center = cones[i]
				ui.conetexts[i]._x = cones[i][0]
				ui.conetexts[i]._y = cones[i][1]
			ui.conesChanged = False
	
		if ui.routeChanged:
			for i in range(len(route)):
				leg = route[i]
				if leg['shape'] == 'line':
					A = (leg['from'])
					B = (leg['to'])
					xd,yd = np.transpose([A,B]); 
					ui.legs[i].set_data(xd,yd)
			for leg in route:
				if leg['shape'] == 'arc':
					A = (leg['from'])
					B = (leg['to'])
					C = (leg['center'])
					tA,_ = nav.thetaFromPoint(A, C)
					tB,_ = nav.thetaFromPoint(B, C)
					rdir = leg['rdir']
					r = specs.turning_radius
					nav.drawArc(tA ,tB, rdir, C, r)
			ui.routeChanged = False
	
		if ui.cbaseChanged:
			#bow,stern = nav.lineFromHeading(cbase, heading, specs.deck_length/2)
			bow,stern = nav.lineFromHeading(cbase, heading, specs.deck_length)
			diff = (bow - stern) / 5  # add 4 dots between bow and stern
			jlog.debug(f'diff: {diff}')
			diff = (np.array(bow) - np.array(stern)) / 5  # add 4 dots between bow and stern
			jlog.debug(f'diff: {diff}')
			points = [0,0,0,0,0]
			for i in range(5): points[i] = stern + (diff * i)
			jlog.debug(f'set_offsets: {points}')
			points = np.transpose(points); 
			ui.skateline.set_offsets(points)
			ui.cbaseChanged = False

		ui.refresh_time = time.time()
	jlog.debug(f'plt pause')
	plt.pause(ui_pause)  # redraw and time.sleep()

def respondToKeyboard():
	global autopilot
	key = ui.eventkey
	ui.eventkey = False
	helm_incr = 2

	if key == 'q':
		kill('UI: kill')

	elif key == 'ctrl+c':
		kill('UI: kill interrupt')

	elif key == 'c':
		ts = time.strftime("%Y%m%d-%H%M%S")
		ui.fig.savefig(fname.replace('%timestamp%', ts))
		jlog.info(f'UI: screen capture {ts}')

	elif key == 'a':
		autopilot = True
		jlog.info(f'UI: autopilot on')

	elif key == 'o':
		autopilot = False
		jlog.info(f'UI: autopilot off')

	elif key == 'left':
		autopilot = False
		newhelm = max(-90, helm - helm_incr)
		sendCommandToSk8(HELM, newhelm)
		jlog.info(f'UI: helm port {helm_incr} degree: {helm} {roll}')

	elif key == 'right':
		autopilot = False
		newhelm = min(90, helm + helm_incr)
		sendCommandToSk8(HELM, newhelm)
		jlog.info(f'UI: helm starboard {helm_incr} degree: {helm} {roll}')

	elif key == 'up':
		newhelm = 0
		sendCommandToSk8(HELM, newhelm)
		jlog.info('UI: helm amidships')

	return key

