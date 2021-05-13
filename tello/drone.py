''' 
drone.py - class Drone, drive the Tello drone.  see documentation below. 
'''
import socket
import time
from time import strftime
import threading 
import sys
import numpy as np
import cv2 as cv
import struct
from hippocampus import Hippocampus
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
use_hippocampus = True  
use_ui = True        # screen driven by hippocampus, kill switch handled by main here
save_frame = True    # frame and training data is saved by hippocampus
save_train = False 
save_mission = True  # mission datat is saved by drone

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
	def __init__(self): # override
		self.state = 'init'  # open, run, stop, crash
		logging.info('telemetry object initializing')
		self.sock  = False
		threading.Thread.__init__(self)
		self.baro_base = 0
		self.lock = threading.Lock()
		self.data = {
			'n':253253,       # custom stat, count of data received 
			'agl':310,        # custom stat, differential baro
			'pitch':-2,
			'roll':-2,
			'yaw':2,
			'vgx':0,
			'vgy':0,
			'vgz':0,
			'templ':62,
			'temph':65,
			'tof':6553,       # height in cm, time of flight, typical range 10 to 56
			'h':0,            # height in cm, always 0
			'bat':42,
			'baro':404.45,    # height in cm, range 322.41 to 323.34 or 321.53 to 322.11
			'time':0,
			'agx':-37.00,
			'agy':48.00,
			'agz':-1008.00
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

			sdata = data.strip().decode('utf-8')
			ddata = universal.unpack(sdata)
			agl = self.calcAgl(ddata)
			ddata['agl'] = agl
			ddata['n'] = count

			self.lock.acquire()
			self.ddata = ddata
			self.sdata = sdata
			self.lock.release()

		logging.info(f'telemetry thread {self.state}')
		self.sock.close()
		logging.info('telemetry socket closed')
	
	def get(self):
		self.lock.acquire()
		ddata = copy.deepcopy(self.ddata)
		sdata = copy.deepcopy(self.sdata)
		self.lock.release()
		return (ddata,sdata)

	def calcAgl(self, data):
		# calc AGL per the barometer reading 
		#    tello baro is assumed to be MSL in meters to two decimal places 
		#    the elevation of Chiang Mai is 310 meters 
		baro = int(data['baro'] * 1000) # m to mm, float to int 
		agl = min_agl
		if not self.baro_base: 
			self.baro_base = baro 
		else: 
			agl = baro - self.baro_base 
			agl = max(agl,min_agl)
		return agl

class Video(threading.Thread):
	def __init__(self, drone): # override
		self.drone = drone 
		self.stream = False
		self.state = 'init' # init, run, stop, crash
		self.hippocampus = False
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

		# create mission frames folder
		self.dirframe = universal.makedir('frame')

	def stop(self):
		self.state = 'stop'
	
	def run(self): # override  # Video::run() - this is the main loop, does navigation and flying
		# start hippocampus
		if use_hippocampus:
			self.hippocampus = Hippocampus( use_ui, save_train)
			self.hippocampus.start()
	
		logging.info(f'video thread started')
		self.state = 'run'
		timestart = time.time()
		timeprev = timestart
		framenum = 0
		while self.state == 'run': 
			# Capture frame-by-frame
			framenum += 1
			ret, frame = self.stream.read()
			if not ret:
				logging.error('Cannot receive frame.  Stream end?. Exiting.')
				self.state == 'crash'
				break

			# get telemetry
			ddata, sdata = self.drone.telemetry.get()

			# detect objects, build map, draw map
			ovec = (0,0,0,0)
			if self.hippocampus:
				# detect objects, build map, draw map
				ovec,rccmd = self.hippocampus.processFrame(frame, framenum, ddata)

				# stop immediatly if lost
				#if rccmd == 'land':
				#	self.drone.cmd.do('land')
				#	self.state == 'stop'
				#	break;

				# fly
				#if self.drone.state == 'airborne' and ovec:
				#	self.drone.cmd.sendCommand(rccmd)

				# save mission data
				if save_mission:
					ts = time.time()
					tsd = ts - timeprev
					src = rccmd.replace(' ','.')
					prefix = f"rc:{src};ts:{ts};tsd:{tsd};n:{ddata['n']};fn:{framenum};agl:{ddata['agl']};"
					timeprev = ts
					logging.log(logging.MISSION, prefix + sdata)

			# save frame
			if save_frame:
				fname = f'{self.dirframe}/{framenum}.jpg'
				cv.imwrite(fname,frame)

			# set frame, framenum, and ovec for use by other threads
			self.lock.acquire()
			self.framenum = framenum
			self.frame = frame
			self.ovec = ovec
			self.lock.release()

			# kill switch
			k = cv.waitKey(1)  # in milliseconds, must be integer
			if k & 0xFF == ord('q'):
				self.state == 'stop'
				break;
		
		logging.info(f'video thread {self.state}') # close or crash
		timestop = time.time()
		logging.info(f'num frames: {framenum}, fps: {int(framenum/(timestop-timestart))}')

		if self.hippocampus:
			self.hippocampus.stop()

		if self.stream and self.stream.isOpened():
			self.stream.release()
			logging.info('video stream closed')

	def get(self):
		self.lock(acquire)
		num = self.framenum
		frame = copy.deepcopy(self.frame)
		self.lock.release()
		return num, frame

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

class Drone:
	def __init__(self):
		self.state = 'start', # start, ready, takeoff, airborne, land, down
		self.video = False
		self.telemetry = False
		self.cmd = False
		self.wifi = False

	def prepareForTakeoff(self):
		logging.info('eyes starting ' + mode)
		timestart = time.time()
		
		# connect to tello
		self.wifi = Wifi(tello_ssid, retry=15)
		connected = self.wifi.connect()
		if not connected:
			return False
		
		# create three objects, one for each socket
		self.telemetry = Telemetry()
		self.cmd = Cmd()
		self.video = Video(self)

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

	#def fly(self, flighttime):
	#	if self.state != 'airborne':
	#		return
	#	self.cmd.flighttime = flighttime
	#	self.cmd.start()

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
		logging.info('eyes shutdown')
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
	# look for startup options
	mode = 'prod'
	for i, arg in enumerate(sys.argv):
		if arg == 'test':
			mode = 'test'

	# missions
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
			'pause 20'
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
			'pause 10\n'
			'land'
	)
	launch = (
			'takeoff\n'
			'up 100\n'
			'land'
	)
	
	# run a mission
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
		flyMission(testvideo, drone) 
		logging.info('mission complete')
	drone.stop() 
	drone.wait()
'''
rename eyes.py, class Eyes, really?
	Video = eyes, visual cortex
	Telemetry = sensory nervous system other than vision
	Cmd = motor nervous system, controlling the eye muscles

commands described in Tello SDK User Guide, online PDF, 1.0 or 2.0
	our Tello has SDK 1.3, includes "rc", but not "sdk?"

mentors:
	github, damiafuentes/djitellopy/tello.py

class Drone embeds three singleton objects, one each for the three Tello sockets:
	Telemetry - public method get() shares the latest telemetry data object
	Video - public method get() shares the latest frame
	Cmd - public method sendCommand(cmd)  shares access to Tello commands

class Drone also embeds Wifi, to connect to the Tello hub 


embeds Hippocampus - should probably be separate, along with Cortex
main flies missions

for effectiveness of Tello Vision Positioning System (VPS):
	lights on
	AC off
	blanket on floor

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

todo:

save video
	on demand, snap command, for testing mirror calibration
	by nth, instead of true/false
	every frame, with or without data
	filename: folder by day, folder by mission, frame number, jpgs only
		mission clock, elapsed time between frames
		file-modified timestamp, does it match mission clock?

mirror calibration, do command, like pause or hover or follow


navigator (new):
	thread
	queue of requests
	default hover method between requests
	one Navigator class: two instances, one for drone, one for skate	

hippocampus.buildMap:
	thread
	mirror correction
	photo angle correction

tello rc command, based on multiple vectors:
	hippocampus:
		drift correction
	navigator:
		course correction	

cmd:
	wait for video started before ready state
		
video:
	avoid "Circular buffer overrun" error
		see: https://stackoverflow.com/questions/35338478/buffering-while-converting-stream-to-frames-with-ffmpegj

navigator states = 'hover', 'home', 'perimeter', 'calibrate'
if flight-time exceeded   # which thread does this?  navigator?
	self.state = 'home'
	proceed to pad
	lower until pad no longer visible
	land

using the Tello rc command is virtual sticks mode or virtual joysticks
DJI has a flight controller sdk for more advanced aircraft
this describes different modes for using virtual joysticks

I have to assume these are the defaults

setRollPitchControlMode(RollPitchControlMode.VELOCITY);
setYawControlMode(YawControlMode.ANGULAR_VELOCITY);
setVerticalControlMode(VerticalControlMode.VELOCITY);
setRollPitchCoordinateSystem(FlightCoordinateSystem.BODY);

coordinate system is body or ground
if ground, x,y are relative to the ground, regardless of the yaw position
if body, x,y are relative to the body, constantly changing as the yaw position changes

defaults
coordinate system: body
vertical control mode: velocity
roll pitch controll mode: velocity
yaw control mode: angular velocity

rc x,y,z,w

x is roll, -100 is full left velocity, +100 is full right velocity
y is pitch, -100 is full back velocity, +100 is full forward velocity
z is vertical, -100 is full down velocity, +100 is full up velocity
w is yaw, -100 is full CCW spin velocity, +100 is full CW spin velocity

numbers are a percentage of full velocity

'''

