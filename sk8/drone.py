''' drone.py - class Drone, drive the Tello drone '''

import socket
import time
from time import strftime
import threading 
import sys
import numpy as np
import cv2 as cv
import struct
from wifi import Wifi
import copy
import universal
import logging

# global constants
tello_ssid = 'TELLO-591FFC'
tello_ip = '192.168.10.1'
safe_battery = 20  # percent of full charge
min_agl = 20  # mm, camera above the ground 

use_rc = True   # rc command vs mission commands

# three ports, three sockets.  firewall must be open to these ports.
telemetry_port = 8890   # UDP server socket to repeatedly send a string of telemetry data
video_port = 11111      # UDP server socket to send a video stream from the camera
cmd_port = 8889         # UDP client socket to receive commands and optionally return a result

telemetry_address = ('',telemetry_port)
telemetry_sock_timeout = 10
telemetry_maxlen = 1518 #?

video_url = f'udp://{tello_ip}:{video_port}'
video_maxlen = 2**16

cmd_address = (tello_ip, cmd_port)
cmd_sock_timeout = 7 # seconds
cmd_takeoff_timeout = 20  # seconds. takeoff slow to return
cmd_time_btw_commands = 0.1  # seconds.  Commands too quick => Tello not respond.
cmd_time_btw_rc_commands = 0.01 # rc command is fire and forget, does not requie a recvfrom
cmd_maxlen = 1518

class Telemetry(threading.Thread):
	def __init__(self, callback): # Thread override
		self.callback = callback
		self.state = 'init'  # open, run, stop, crash
		self.sock  = False
		threading.Thread.__init__(self)
		self.data = {             # source: Tello SDK 2.0 User Guide, online PDF
			'pitch':-2,       # degree of attitude pitch
			'roll':-2,        # degree of attitude roll
			'yaw':2,          # degree of attitude yaw
			'vgx':0,          # the speed of the x axis
			'vgy':0,          # the speed of the y axis
			'vgz':0,          # the speed of the x axis
			'templ':62,       # the lowest temperature in degree Celsius
			'temph':65,       # the highest temperature in degree Celsius
			'tof':6553,       # time of flight distance in cm (typical range 10 to 56)
			'h':0,            # the height in cm (always 0)
			'bat':42,         # the percentage of the current battery level
			'baro':404.45,    # the barometer measurement in cm (range 321.41 to 323.34)
			'time':0,         # the amount of time the motor has been used
			'agx':-37.00,     # the acceleration of the x axis
			'agy':48.00,      # the acceleration of the y axis
			'agz':-1008.00    # the acceleration of the z axis
		}

	def open(self):
		# Create telemetry socket as UDP server
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.settimeout(telemetry_sock_timeout)
		self.sock.bind(telemetry_address) # bind is for server, not client
		self.state = 'open'
		logging.info('telemetry socket open')

	def stop(self):
		self.state = 'stop'

	def run(self): # override
		logging.info(f'telemetry thread started')
		count = 0
		self.state = 'run'
		while self.state == 'run': 
			count += 1
			try:
				data, server = self.sock.recvfrom( telemetry_maxlen)
			except Exception as ex:
				logging.error('telemetry recvfrom failed: ' + str(ex))
				self.state = 'crash'
				break
			self.callback(data,count)

		logging.info(f'telemetry thread {self.state}')
		self.sock.close()
		logging.info('telemetry socket closed')
	
class Video(threading.Thread):
	def __init__(self, callback): # Thread override
		self.callback = callback
		self.stream = False
		self.state = 'init' # init, run, stop, crash
		threading.Thread.__init__(self)
		self.lock = threading.Lock()
		self.framenum = 0
		self.frame = False

	def open(self):
		timestart = time.time()
		logging.info('start video capture')
		self.stream = cv.VideoCapture(video_url)  # BLOCKING takes about 5 seconds
		if not self.stream.isOpened():
			logging.error(f'Cannot open camera. abort. elapsed={time.time()-timestart}')
			self.state = 'crash'
			return False
		self.state = 'open'
		logging.info(f'video capture started, elapsed={time.time()-timestart}')

	def stop(self):
		self.state = 'stop'
	
	def run(self): # Thread override
		logging.info(f'video thread started')
		self.state = 'run'
		timestart = time.time()
		timeprev = timestart
		framenum = 0
		while self.state == 'run': 
			# Capture frame-by-frame
			framenum += 1
			ret, frame = self.stream.read()  # no way to change default 20 second timeout
			if not ret:
				logging.error('Video stream timeout. Exiting.')
				self.state == 'crash'
				break
			self.callback(frame,framenum) # normally the Vision-Motor-Circuit
		
		logging.info(f'video thread {self.state}') # close or crash
		timestop = time.time()
		logging.info(f'num frames: {framenum}, fps: {int(framenum/(timestop-timestart))}')

		if self.stream and self.stream.isOpened():
			self.stream.release()
			logging.info('video stream closed')

class Cmd(threading.Thread):
	def __init__(self): #override
		self.state = 'init' # open, close
		self.sock = False
		self.timestamp = 0
		threading.Thread.__init__(self)
		self.lock = threading.Lock()
		self.flighttime = 0
		self.threshhold = 0

	def close(self):
		self.sock.close()
		self.state = 'close'
		logging.info('cmd socket closed')

	def open(self):
		# Create cmd socket as UDP client (no bind)
		timestart = time.time()
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.settimeout(cmd_sock_timeout)
		self.state = 'open'
		logging.info('cmd socket open')

	# send command to Tello and optionally get return message. BLOCKING, recvfrom is the slow bit
	def sendCommand(self, cmd):
		# make this method reentrant
		self.lock.acquire()

		# the takeoff command is way slow to return, with the tello hanging in the air, 
		# perhaps checking and calibrating itself before returning to the client
		timeout = cmd_sock_timeout
		if cmd == 'takeoff':
			timeout = cmd_takeoff_timeout
			self.sock.settimeout(timeout)

		# the command command sometimes returns a premature packet of bogus data.
		# the battery? command sometimes returns "ok" instead of an integer
		# both can be ignored and retried
		retry = 0
		if cmd == 'command' or cmd == 'battery?':
			retry = 2

		# rc command is fire and forget
		wait = True
		if 'rc' in cmd:
			wait = False

		# pause a moment, sending commands too quickly overwhelms the Tello
		diff = time.time() - self.timestamp
		if diff < self.threshhold:
			logging.debug(f'waiting {diff} between commands')
			time.sleep(diff)
		self.threshhold = cmd_time_btw_commands # set pause self.threshhold for next command
		if 'rc' in cmd:
			self.threshhold = cmd_time_btw_rc_commands

		# send command to socket
		rmsg = 'error'
		timestart = time.time()
		try:
			msg = cmd.encode(encoding="utf-8")
			len = self.sock.sendto(msg, cmd_address)
		except Exception as ex:
			logging.error(f'sendCommand {cmd} sendto failed:{str(ex)}, elapsed={time.time()-timestart}')
		else:
			if not wait:
				logging.info(f'sendCommand {cmd} complete, elapsed={time.time()-timestart}')
				rmsg = 'ok'
			else:
				# read response from command
				for r in range(0,retry+1):
					n = f'retry={r},' if r else ''
					try:
						data, server = self.sock.recvfrom(cmd_maxlen)
					except Exception as ex:
						logging.error(f'sendCommand {cmd} recvfrom failed: {str(ex)}, {n} elapsed={time.time()-timestart}')
						break
					else:
						if b'\xcc' in data:
							# bogus data: b'\xcc\x18\x01\xb9\x88V\x00\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00I\x00\x00\xa7\x0f\x00\x06\x00\x00\x00\x00\x00W\xbe'
							logging.error(f'sendCommand {cmd} recvfrom returned bogus data, {n} elapsed={time.time()-timestart}')
							continue
	
						# sometimes, data received is from the previous command
						if cmd == 'battery?' and b'ok' in data:
							logging.error(f'sendCommand {cmd} recvfrom returned "ok", {n} elapsed={time.time()-timestart}')
							continue
	
						try:
							rmsg = data.decode(encoding="utf-8")
						except Exception as ex:
							logging.error(f'sendCommand {cmd} decode failed: {str(ex)}, {n} elapsed={time.time()-timestart}')
							break;
	
						# success
						rmsg = rmsg.rstrip() # battery? returns string plus newline
						logging.info(f'sendCommand {cmd} complete: {rmsg}, {n} elapsed={time.time()-timestart}')
						if cmd == 'takeoff':
							self.sock.settimeout(cmd_sock_timeout)
						break;

		self.timestamp = time.time()
		self.lock.release()
		return rmsg;

def empty(data,count):
	pass

class Drone:
	def __init__(self,telemetry_callback=empty,video_callback=empty):
		self.state = 'start', # start, ready, takeoff, airborne, land, down
		self.wifi = False

		# create three objects, one for each socket
		self.telemetry = Telemetry(telemetry_callback)
		self.cmd = Cmd()
		self.video = Video(video_callback)

	def prepareForTakeoff(self):
		logging.info('drone starting')
		timestart = time.time()
		
		# connect to tello
		self.wifi = Wifi(tello_ssid, retry=15)
		connected = self.wifi.connect()
		if not connected:
			return False
		
		# open cmd socket
		self.cmd.open()

		# put the Tello into "command" mode, which starts the telemetry stream
		result = self.cmd.sendCommand("command")
		if result != 'ok':
			logging.info('Tello failed to enter "command" mode.  abort.')
			return False
		logging.info('Tello is in "command" mode')

		# open telemetry socket and start thread	
		self.telemetry.open()
		self.telemetry.start() 

		# check battery
		batt = self.cmd.sendCommand("battery?")
		if int(batt) < safe_battery:
			logging.error('battery low.  aborting.')
			return False
		logging.info('battery check goahead')

		# start video
		so = self.cmd.sendCommand("streamon")
		if so != 'ok':
			logging.error('tello streamon failed.  aborting.')
			return False

		# open video socket and start thread
		self.video.open() # blocks until started, about 5 seconds
		self.video.start()
		
		# can we wait for video thread to start here?

		# ready for takeoff:
		#     command mode, good battery, video running, telemetry running, ui open
		self.state = 'ready'
		logging.info(f'ready for takeoff, elapsed={time.time()-timestart}')
		return True

	def wait(self):  # BLOCKING until sub threads stopped
		if self.telemetry.is_alive():
			self.telemetry.join()
		if self.video.is_alive():
			self.video.join()

	def stop(self):
		if self.state == 'airborne':
			self.do('land')
		self.telemetry.stop()
		self.video.stop()
		self.cmd.close()
		logging.info('drone shutdown')
		logging.info('restoring wifi')
		self.wifi.restore()

	def do(self, cmd):
		if 'takeoff' in cmd:
			self.state = 'takeoff'
		if 'land' in cmd:
			self.state = 'land'
		result = self.cmd.sendCommand(cmd)
		if 'takeoff' in cmd:
			self.state = 'airborne'
		if 'land' in cmd:
			self.state = 'down'

if __name__ == '__main__':
	takeoffland = (
			'takeoff\n'
			'land'
	)
	testheight = (
			'sdk?\n'
			'rc 0 0 0 0\n'  # left/right, forward/back, up/down, yaw; -100 to 100
			'height?\n'
			'tof?\n'
			'baro?'
	)
	demo = (
			'takeoff\n'
			'up 20\n'
			'cw 90\n'
			'right 20\n'
			'cww 90\n'
			'forward 20\n'
			'down 40\n'
			'land'
	)
	testvideo = (
			'pause 60'
	)
	missioncmds = (
			'takeoff\n'
			'go left\n'
			'pause 2\n'
			'go right\n'
			'pause 2\n'
			'go forward\n'
			'pause 2\n'
			'go back\n'
			'pause 2\n'
			'go hold\n'
			'pause 2\n'
			'land'
	)
	pitchroll = (
			'go startmotors\n'
			'pause 2\n'
			'go liftoff\n'
			'pause 2\n'
			'go hold\n'
			'pause 2\n'
			'go left\n'
			'pause 1\n'
			'go right\n'
			'pause 1\n'
			'go forward\n'
			'pause 2\n'
			'go back\n'
			'pause 1\n'
			'go forward\n'
			'pause 0.5\n'
			'go hold\n'
			'pause 1\n'
			'land'
	)
	vertyaw = (
			'go startmotors\n'
			'pause 2\n'
			'go liftoff\n'
			'pause 2\n'
			'go hold\n'
			'pause 2\n'
			'go up\n'
			'pause 1\n'
			'go down\n'
			'pause 1\n'
			'go cw\n'
			'pause 2\n'
			'go ccw\n'
			'pause 1\n'
			'go hold\n'
			'pause 1\n'
			'go land'
	)
	stop = (
			'go startmotors\n'
			'pause 2\n'
			'emergency'
	)
	hover = (
			'go startmotors\n'
			'pause 2\n'
			'go liftoff\n'
			'pause 2\n'
			'land'
	)
	launch = (
			'takeoff\n'
			'up 100\n'
			'land'
	)
	
	def flyMission(s, drone):
		a = s.split('\n')
		for directive in a:
			logging.info(f'mission: {directive}')
			if 'pause' in directive:
				n = directive.split(' ')[1]
				time.sleep(float(n))
			#elif 'hover' in directive:
			#	n = directive.split(' ')[1]
			#	drone.fly(int(n))
			elif 'go' in directive:
				speed = 50
				d = directive.split(' ')[1]
				
				# left stick
				if d == 'left'   : x,y,z,w = (-speed,0,0,0)
				if d == 'right'  : x,y,z,w = (speed,0,0,0)
				if d == 'forward': x,y,z,w = (0,speed,0,0)
				if d == 'back'   : x,y,z,w = (0,-speed,0,0)

				# right stick
				if d == 'up'     : x,y,z,w = (0,0,speed,0)
				if d == 'down'   : x,y,z,w = (0,0,-speed,0)
				if d == 'cw'     : x,y,z,w = (0,0,0,speed)
				if d == 'ccw'    : x,y,z,w = (0,0,0,-speed)

				if d == 'hold'   : x,y,z,w = (0,0,0,0)
				if d == 'startmotors' : x,y,z,w = (-100,-100,-100,100) # both sticks down and inward
				if d == 'stopmotors1' : x,y,z,w = (-100,-100,-100,100) # same as startmotors
				if d == 'stopmotors2' : x,y,z,w = (0,-100,0,0) # left stick full back
				if d == 'liftoff'     : x,y,z,w = (0,0,speed,0)
				if d == 'land'        : x,y,z,w = (0,0,-40,0)

				scmd = f'rc {x} {y} {z} {w}'
				drone.cmd.sendCommand(scmd)
				if d == 'liftoff':
					drone.state = 'airborne'
			else:
				drone.do(directive)

	universal.configureLogging()
	drone = Drone()
	started = drone.prepareForTakeoff()
	if started:
		logging.info('start mission')
		flyMission(hover, drone) 
		logging.info('mission complete')
	drone.stop() 
	drone.wait()
'''
todo:
	pass a callback to Video::run()
		execute SensoryMotorCircuit()
		replace all run()
		remove Hippocampus import
	pass a callback to Telemetry::run()
		send string to Cerebrum
	
	rename
		Video -> Eyes
		Telemetry -> Ears
		Cmd -> Neck
		Drone -> ?
		drone.py -> ?

	video: avoid "Circular buffer overrun" error
		see: https://stackoverflow.com/questions/35338478/buffering-while-converting-stream-to-frames-with-ffmpegj
--------
mentors:
	github, damiafuentes/djitellopy/tello.py
	github, murtazahassan/

class Drone 
	embeds three singleton objects, one each for the three Tello sockets:
		Telemetry -
			Ears, sensory nervous system, sensing speed, acceleration, attitude
			thread, client socket
			transmits telemetry string 5 times per second
		Video -
			Eyes, vision
			thread, client socket
			transmits video stream at 40 fps
		Cmd -
			Neck, motor nervous system, aiming eyes
			no thread, server socket
			public method sendCommand(cmd)  shares access to Tello commands
	also embeds:
		Wifi - to connect to the Tello hub 

	__main__ - flies pre-programmed missions, with no position feedback

	data saving:
		frames, already flipped for mirror, no resize
		training file, detected objects, must match frame
		mission log, logging level 17 only
		debug log, logging all levels
		Note: console log displays levels except debug and mission.
		Note: frames and mission log can be used to rerun a mission in the simulator.

about the Tello drone
	mfg by DJI and Ryze, both in Shenghen
	
	commands described in Tello SDK User Guide, online PDF, 1.0 or 2.0
		our Tello has SDK 1.3, includes "rc", but not "sdk?"
	
	for effectiveness of Tello Vision Positioning System (VPS):
		bright, soft, indirect sunlight
		AC and fan off, no wind
		blanket on floor, non-shiny surface
	
	Tello LED codes, see User Guide:
		red,grn,yel   blink alternating   startup diagnostics, 10 seconds
		yellow        blink quickly       wifi ready, not connected, signal lost
		green         blink slowly        wifi connected
		
		green         blink double        VPS on
		yellow        blink slowly        VPS off
		
		red           blink slowly        low battery
		red           blink quickly       critically low battery
		red           solid               critical error
		
		blue          solid               charging complete
		blue          blink slowly        charging
		blue          blink quickly       charging error

	virtual radio control via two joysticks, four axes:
		"rc x,y,z,w"
			where each each parameter is a percentage of full velocity, forward or reverse
			0 means zero velocity, ie. hold current position
		x is roll,     -100 is full left velocity,     +100 is full right velocity
		y is pitch,    -100 is full back velocity,     +100 is full forward velocity
		z is vertical, -100 is full down velocity,     +100 is full up velocity
		w is yaw,      -100 is full CCW spin velocity, +100 is full CW spin velocity

	The Tello coordinate system is "ground".  See below for explanation.
	
about DJI Flight Controllers (FC) in general:
	One way to fly is called "virtual sticks mode" or "virtual joysticks".
	DJI has a flight controller SDK. (I don't think it's available for Tello.)
		It describes different modes for using virtual joysticks.
	
	joysticks can be used in different ways 	
		with different FC settings to satisfy pilot preference
	
	the defaults are usually:
		setRollPitchControlMode( RollPitchControlMode.VELOCITY);
		setYawControlMode( YawControlMode.ANGULAR_VELOCITY);
		setVerticalControlMode( VerticalControlMode.VELOCITY);
		setRollPitchCoordinateSystem( FlightCoordinateSystem.BODY);
	
	coordinate system is body or ground
		if ground, x,y are relative to the ground, regardless of the yaw position
		if body, x,y are relative to the body, constantly changing as the yaw position changes
'''
