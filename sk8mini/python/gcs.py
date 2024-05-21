'''
gcs.py  ground control station

runs on laptop

connect to the dongle via serial port

functions:
	receive AHRS data sk8 via serial port dongle running gcs.ino
	connect to awacs webserver and download photo
	detect donut and cone positions from the photo
	detect wheelbase center by combining donut center, helm angle, roll angle
	navigate
	pilot
	send pilot commands to sk8 through the serial port dongle

	gcs
		kill - Ctrl-C
		visualize log - logger to laptop display
		download photos and labels from awacs and save to disk for ai training
		(opt) visualize arena - matplotlib
		(opt) manual piloting - matplotlib incl keyboard and mouse
	
	awacs
		take photos
		georeference to cover arena
		object detection
	
	sk8
		setup - calibration
		get arena map from awacs
		get position from awacs
		dead reckon position
		command - choose patterns, plan route
		navigate - plot route
		pilot

throttle adjustment is relative to roll, not helm
	therefore, perhaps we should go back to separate commands
	if doing async, we need events
		onRoll - adjust throttle depending on roll
		onHeading - adjust helm to keep course bearing and/or turn radius
		onPosition - override dead-reckoning position

----------------
sources

object detection:
	folder:  ~/webapps/robots/robots/sk8mini/awacs/detect/
		testconvolve.py  - find donut
		idir = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
		odir = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/'
	scanorm.py - scan a folder of images and a folder of labels, draw the label circle onto the image
	still need the latest find cone algorithm...

navigate:
	~/webapps/robots/robots/autonomy/
		hippoc.py - sim skate path around cones, with video out, using matplotlib and FuncAnimation
		nav.py - library of trigonometry used in navigation

pilot:
	~/webapps/robots/robots/sk8mini/pilot
		pilot.ino - helm and throttle implemented via espwebserver
		pilot.py - manual piloting via keyboard as webserver client, using curses

camera:
	~/webapps/robots/robots/sk8mini/awacs/cam.py

---------------------
todo:

x rename cam.py to awacs.py

x rename test.py to testAwacs.py

x pull testAwacs.py code into gcs.py

x combine awacs + cam2.py + testthreading.py

x pull testAwacs.py code into main() of awacs.py library

x delete cam2.py, testthreading.py, testAwacs.py

split gcs.py into gcs.py + skate.py

implement sk8mini_specs, sk8math, or sk8.py library, or fold into skate.py

change class PILOT to class CMD

add onHelm: adjust right-throttle

finish figure 8 pattern for calibration, with right throttle adjustment

add navigation
	dead reckoning
		keep list of recent commands
		with each new command, calc new position by adding previous command

add piloting to gcs.py

feasibiliry of writing images to micro sd card on drone
	size of photos for 10  minut performenace
	size of sd card
	can esp32 connect to a microsd card
	are there arduino demos of writing to an sd card

pilot: throttle adjust
	onRoll
	change command struture: separate helm and throttle commands

event-driven
	On roll, adjust throttle
	On heading, dead reckon
	On time elapsed, 
	On position, pilot 
	On cone rounded, navigate

Lambert azimuthal equal-area projection centered on the North Pole. 
	Map: Caitlin Dempsey.
	https://www.geographyrealm.com/types-map-projections/
	https://projectionwizard.org/

minimalist shoe features:
	wide toe box
	zero-drop (flat)
	flexible sole

'''

import serial
import time
import logger
import awacs

# structure types

class AHRS:
	heading	= 9999.0
	roll	= 0.0
	pitch	= 0.0
	sys	= 0
	gyro	= 0
	accel	= 0
	mag	= 0

class PILOT:
	helm 	= 0	# -90 to +90, negative:port, positive:starboard, zero:amidships
	throttle= 0	# -90 to +90, negative:astern, positive:ahead, zero:stop

# global variables

scomm = serial.Serial(port='/dev/ttyUSB0',   baudrate=115200, timeout=.3)
pilot = PILOT()
ahrs = AHRS()
ahrs_buffer_minimum = 10
magnetic_declination = -1.11 # from magnetic-declination.com depending on lat-lon

# state management

STATE_NONE		= 0
STATE_STARTING		= 1
STATE_CALIBRATING	= 2
STATE_GYRO_CALIBRATED	= 3
STATE_MAG_CALIBRATED	= 4
STATE_CALIBRATED	= 5
STATE_SETUP_COMPLETE	= 6
STATE_KILLED		= 7

state_texts = [
	"none",
	"starting",
	"calibrating",
	"gyro calibrated",
	"mag calibrated",
	"calibrated",
	"setup complete",
	"killed"
]

state = STATE_NONE

def setState(newstate):
	global state
	if newstate > state:
		state = newstate
		logger.info(f'gcs state: {state_texts[state]}')

# ----- 

def sendPilot(newhelm, newthrottle):
	global pilot
	pilot.helm = newhelm
	pilot.throttle = newthrottle
	s = f'{newhelm}\t{newthrottle}' 
	scomm.write(bytes(s, 'utf-8'))
	logger.info(f'gcs sendPilot sent thru serial: {s}')

def getAhrs():
	global ahrs
	if scomm.in_waiting < ahrs_buffer_minimum:   # number of bytes in the receive buffer
		# sk8.ino sends data only when it changes
		return False

	b = scomm.readline()	# serial read to \n or timeout, whichever comes first
	#logger.info(f'len {len(b)}')
	if len(b) > 0:
		s = b.decode("utf-8")	# to tab-separated string
		lst = s.split()		# parse into global struct
		ahrs.heading	= float( lst[0])
		ahrs.roll	= float( lst[1])
		ahrs.pitch	= float( lst[2])
		ahrs.sys	= int( lst[3])
		ahrs.gyro	= int( lst[4])
		ahrs.accel	= int( lst[5])
		ahrs.mag	= int( lst[6])

	# the BRO055 does NOT adjust for magnetic declination, so we do that here
	ahrs.heading += magnetic_declination
	if ahrs.heading < 0:
		ahrs.heading = (360 - ahrs.heading)

	logger.info(f'gcs heading:{ahrs.heading:.2f}, roll:{ahrs.roll}, gyro:{ahrs.gyro}, mag:{ahrs.mag}')
	return True


# ---- calibration

# the BRO055 does three calculations at random times in the background: 
#	1. gyro calculation, easy, just let it sit still for a few seconds
#	2. mag calculation, hard, move in a figure eight pattern repeatedly
#	3. accel calculation, harder, we dont evey try

FIGURE_8_HALF_TIME = 5
calibration_started = 0
maneuver_started = 0

def calibrateMag():
	global calibration_started, maneuver_started
	if ahrs.mag >= 3 or ((calibration_started > 0) and (time.time() - calibration_started) > 20):
		sendPilot( 0, 0)
		setState(STATE_MAG_CALIBRATED)
		return

	if calibration_started <= 0:
		calibration_started = time.time()
		maneuver_started = calibration_started
		sendPilot( 90, 23)
	else:
		if time.time() - maneuver_started > FIGURE_8_HALF_TIME:
			newhelm = (0 - pilot.helm)  # reverse
			sendPilot( newhelm, 23)
			maneuver_started = time.time()

def calibrateGyro():
	if ahrs.gyro < 3 and state < STATE_GYRO_CALIBRATED:
		return
	else:
		setState(STATE_GYRO_CALIBRATED)

def setupSk8():
	ahrs_updated = getAhrs()

	if state == STATE_CALIBRATING:
		calibrateGyro()

	elif state == STATE_GYRO_CALIBRATED:
		calibrateMag()

	else:
		setState(STATE_CALIBRATED)
		setState(STATE_SETUP_COMPLETE)

def setupAwacs():
	awacs.net = 'awacs'
	awacs.user = 'john'
	awacs.pw = 'invincible'
	awacs.url = 'localhost:py'
	awacs.folder = 'home/john/media/webapps/sk8mini/awacs/photos/'
	awacs.start()

def setup():
	logger.setup(True,False)

def shutdown():
	awacs.stop()

#def cam.isPhotoAvailable():
#	return cam.available
#
#def cam.getPhoto():
#	return photo

def loop():
	ahrs_updated = getAhrs()
	if not ahrs_updated:
		return;

#	if cam.photoavailable():
#		photo = cam.getAerialPhoto()
#		objects = detectObjects(photo) # sk8 and cones
	logger.info(f'gcs {awacs.num.value}')
	time.sleep(.3)

	#plan = calcPlan(cones, order, sides)
	#route = plotRoute(plan)
	#drawArena(plan)
	#drawRoute(route)

	sendPilot(90,23)

def main():
	try:
		setup()

		setState( STATE_STARTING)
		setState( STATE_CALIBRATING)

		setupAwacs()

		while state < STATE_CALIBRATED:
			setupSk8()
	
		while state < STATE_KILLED:
			loop()

	except KeyboardInterrupt:
		logger.info('')
		setState( STATE_KILLED)
		sendPilot( 0, 0)

	finally:
		shutdown()

if __name__ == '__main__':
	main()

