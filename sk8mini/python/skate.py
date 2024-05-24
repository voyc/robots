'''
skate.py

runs in the skate_process, launched by gcs.py 
someday will run on the sk8 along with sk8.ino

the BRO055 does three calibrations at random times in the background: 
	1. gyro calibration, easy, just let it sit still for a few seconds
	2. mag calibration, hard, move in a figure eight pattern repeatedly
	3. accel calibration, harder, we dont evey try


python exceptions

the purpose of catching an exception, is to prevent the program from interrupting
so if you want the program to interrupt, you must take action
	1. raise - run the finally clause and then goto outer try
	2. return - rund the finally clause and then return from the function
	3. break, continue, return - finally executes

A finally clause is always executed before leaving the try statement.
When an exception has occurred in the try clause and has not been handled by an except clause
(or it has occurred in a except or else clause), 
it is re-raised after the finally clause has been executed. 
The finally clause is also executed “on the way out” 
when any other clause of the try statement is left via a break, continue or return statement. 


You can leave the except clause with raise, return, break, or continue.
In any case, the finally clause will execute.


'''

import signal
import os
import serial
import time

import jlog
from smem import *

# types
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

# global constants, set by gcs.py argparse before skate_process is started
verbose	= True
quiet	= False
port	= '/dev/ttyUSB0'  # serial port for dongle
baud	= 115200
serialtimeout = 3
serialminbytes = 10
declination = -1.11 # from magnetic-declination.com depending on lat-lon

minimum_skate_time = .1

# global constants, initialized one-time within skate_process
scomm = False
pilot = PILOT()
ahrs = AHRS()

# calibration constants and variables
FIGURE_8_HALF_TIME = 5
MAG_CALIBRATION_MAX_TIME = 10
FULLY_CALIBRATED = 3

gyro_calibrated = 0
mag_calibrated = 0
calibration_started = 0
maneuver_started = 0

# ---- comm -----

def sendPilotCommandToSk8(newhelm, newthrottle):
	global pilot
	pilot.helm = newhelm
	pilot.throttle = newthrottle
	s = f'{newhelm}\t{newthrottle}' 
	if not scomm:
		jlog.info(f'skate: pilot command not sent, no serial')
	else:
		scomm.write(bytes(s, 'utf-8'))
		jlog.info(f'skate: pilot command sent to sk8 thru serial: {s}')

def getAhrsFromSk8():
	if scomm.in_waiting < serialminbytes:   # number of bytes in the receive buffer
		# sk8.ino sends data only when it changes - NOT
		return False

	b = scomm.readline()	# serial read to \n or timeout, whichever comes first
	#jlog.info(f'len {len(b)}')
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
	ahrs.heading += declination
	if ahrs.heading < 0:
		ahrs.heading = (360 - ahrs.heading)

	jlog.info(f'skate: heading:{ahrs.heading:.2f}, roll:{ahrs.roll}, gyro:{ahrs.gyro}, mag:{ahrs.mag}')
	return True

def connectSerial():
	global scomm
	scomm = serial.Serial(port=port, baudrate=baud, timeout=serialtimeout)

	# test the connection through dongle to the sk8
	time.sleep(.5)
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
		sendPilotCommandToSk8( 0, 0)
		return True

	if ((calibration_started > 0) and (time.time() - calibration_started) > MAG_CALIBRATION_MAX_TIME):
		sendPilotCommandToSk8( 0, 0)
		raise Exception('magnometer calibration timed out')

	if calibration_started <= 0:
		calibration_started = time.time()
		maneuver_started = calibration_started
		sendPilotCommandToSk8( 90, 23)
	else:
		if time.time() - maneuver_started > FIGURE_8_HALF_TIME:
			newhelm = (0 - pilot.helm)  # reverse
			sendPilotCommandToSk8( newhelm, 23)
			maneuver_started = time.time()

def calibrateGyro():
	if ahrs.gyro >= 3:
		return True
	nudgeHelm()
	return False

# ---- process target -----

def skate_main(timestamp, positions):
	global scomm
	try:
		jlog.setup(verbose, quiet)
		jlog.debug(f'skate: starting process id: {os.getpid()}')
		signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore KeyboardInterrupt
		scomm = connectSerial()
		if not scomm:
			raise Exception('serial port connection failed')
		jlog.debug(f'skate: serial port connected')
			
		while True:
			if timestamp[TIME_KILLED]:
				jlog.info(f'skate: stopping due to kill')
				break
			if gyro_calibrated and mag_calibrated:
				break
			calibrate()

		while True:
			if timestamp[TIME_KILLED]:
				jlog.info(f'skate: stopping due to kill')
				break
			navigate()
			pilot()

		jlog.debug("skate: drop out of main loop")

	except KeyboardInterrupt:
		jlog.error('never happen')

	except Exception as ex:
		jlog.error(f'skate: exception: {ex}')
		timestamp[TIME_KILLED] = time.time()
	try:
		sendPilotCommandToSk8( 0, 0)
	except Exception as ex:
		jlog.error(f'skate: shutdown exception: {ex}')

	jlog.info(f'skate: main exit')

# ---- pilot -----

def pilot():
	jlog.info(f'skate: pilot')
	
def nudgeHelm():
	sendPilotCommandToSk8( 5, 0)
	time.sleep(.1)
	sendPilotCommandToSk8( 0, 0)

def pause():
	pass

def figure8():
	pass

# ---- navigator -----
	
def navigate():
	jlog.info(f'skate: navigate')
	


