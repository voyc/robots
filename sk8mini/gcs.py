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
	
-------------------------
ui:
	print ?
	matplotlib ?
	curses ?
	kill switch
	manual remote controls ?
	map
	attitude (roll)

starting
calibrating mag
calibrating gyro
starting servos
ready

starting
connecting to webserver
getting first photo
finding center
ready


'''

import serial
import time

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
		print(f'state: {state_texts[state]}')

# ----- 

def sendPilot(newhelm, newthrottle):
	global pilot
	pilot.helm = newhelm
	pilot.throttle = newthrottle
	s = f'{newhelm}\t{newthrottle}' 
	scomm.write(bytes(s, 'utf-8'))
	print(f'sendPilot sent thru serial: {s}')

def getAhrs():
	global ahrs
	if scomm.in_waiting < ahrs_buffer_minimum:   # number of bytes in the receive buffer
		# sk8.ino sends data only when it changes
		return False

	b = scomm.readline()	# serial read to \n or timeout, whichever comes first
	#print(f'len {len(b)}')
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

	print(f'{time.time()}: heading:{ahrs.heading:.2f}, roll:{ahrs.roll}, gyro:{ahrs.gyro}, mag:{ahrs.mag}')
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
	if ahrs.mag >= 3:
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

def setup():
	ahrs_updated = getAhrs()

	if state == STATE_CALIBRATING:
		calibrateGyro()

	elif state == STATE_GYRO_CALIBRATED:
		calibrateMag()

	else:
		setState(STATE_CALIBRATED)
		setState(STATE_SETUP_COMPLETE)

def shutdown():
	pass

def cam.isPhotoAvailable():
	return cam.available

def cam.getPhoto():
	return photo

def loop():
	ahrs_updated = getAhrs()
	if not ahrs_updated:
		return;

	if cam.photoavailable():
		photo = cam.getAerialPhoto()
		objects = detectObjects(photo) # sk8 and cones

	#plan = calcPlan(cones, order, sides)
	#route = plotRoute(plan)
	#drawArena(plan)
	#drawRoute(route)

	sendPilot(90,23)

def main():
	try:
		setState( STATE_STARTING)
		setState( STATE_CALIBRATING)

		while state < STATE_CALIBRATED:
	#		setup()
	
		while state < STATE_KILLED:
			loop()

	except KeyboardInterrupt:
		print()
		setState( STATE_KILLED)
		sendPilot( 0, 0)

	finally:
		shutdown()

if __name__ == '__main__':
	main()

