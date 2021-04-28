''' drone.py - class Drone, drive the tello drone. 
embeds Wifi
embeds Hippocampus - should probably be separate, along with Cortex
main flies missions

for stability:
	- lights on
	- AC off
	- blanket on floor

sendCommand
	only command requires retry
	only takeoff requires timeout change
	simplify messaging for all other commands

navigator with 
	thread
	queue of requests
	default hover method between requests

technically, the navigator will be  driving the sk8, not the drone
	we need a dual navigator function, one for the drone, one for the sk8

# todo: add a mission log, comprised of cmd and telemetry data
# todo: add replay mission feature, using mission log combined with saved video
		
Tello LED codes
red, green, yellow   blink alternating   startup diagnostics, 10 seconds
yellow               blink quickly       wifi ready, not connected, signal lost
green                blink slowly        wifi connected

green                blink double        VPS on, Vision Positioning System 
yellow               blink slowly        VPS off

red                  blink slowly        low battery
red                  blink quickly       critically low battery
red                  solid               critical error

blue                 solid               charging complete
blue                 blink slowly        charging
blue                 blink quickly       charging error
'''

import socket
import time
from time import strftime
from datetime import datetime
import threading 
import sys
import numpy as np
import cv2 as cv
import struct
import logging
from hippocampus import Hippocampus
from wifi import Wifi

# global constants
tello_ssid = 'TELLO-591FFC'
tello_ip = '192.168.10.1'
safe_battery = 20

# three ports, three sockets.  firewall must be open to these ports.
telemetry_port = 8890   # UDP server socket to repeatedly send a string of telemetry data
video_port = 11111      # UDP server socket to send a video stream from the camera
cmd_port = 8889         # UDP client socket to receive commands and optionally return a result

telemetry_address = ('',telemetry_port)
telemetry_sock_timeout = 10
telemetry_maxlen = 1518 #?
telemetry_log_nth = 60

video_url = f'udp://{tello_ip}:{video_port}'
video_maxlen = 2**16

cmd_address = (tello_ip, cmd_port)
cmd_sock_timeout = 7 # seconds
cmd_takeoff_timeout = 20  # seconds. takeoff slow to return
cmd_time_btw_commands = 0.1  # seconds.  Commands too quick => Tello not respond.
cmd_maxlen = 1518

class Telemetry(threading.Thread):
	def __init__(self): # override
		self.state = 'init'  # open, run, stop, crash
		logging.info('telemetry object initializing')
		self.sock  = False
		self.baro_base = False
		self.baro_temp_array = []
		self.baro_height = False
		threading.Thread.__init__(self)
		self.baro_base = 0
		self.lock = threading.Lock()
		self.data = {
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
			'agz':-1008.00,
			'agl':310         # custom stat added by us
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
			try:
				data, server = self.sock.recvfrom( telemetry_maxlen)
			except Exception as ex:
				logging.error('telemetry recvfrom failed: ' + str(ex))
				self.state = 'crash'
				break
			sdata = data.strip().decode('utf-8')
			ddata = self.unpack(sdata)
			self.calcAgl(ddata)
			self.lock.acquire()
			self.data = ddata
			self.lock.release()
	
			# log
			count += 1
			if count >= telemetry_log_nth:
				count = 0
				logging.debug(sdata)

		logging.info(f'telemetry thread {self.state}')
		self.sock.close()
		logging.info('telemetry socket closed')
	
	def get(self):
		self.lock.acquire()
		data = deepcopy.deepcopy(self.data)
		self.lock.release()
		return data

	def unpack(self, sdata):
		# data=b'pitch:-2;roll:-2;yaw:2;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:6553;h:0;bat:42;baro:404.45;time:0;agx:-37.00;agy:48.00;agz:-1008.00;'
		adata = sdata.split(';')      # array
		ddata = {}                    # dict
		for stat in adata:
			if len(stat) <= 2: # last item is cr+lf
				break
			name,value = stat.split(':')
			if name in ['baro','agx','agy','agz']:
				ddata[name] = float(value);
			else:
				ddata[name] = int(value);
		return ddata
	
	def calcAgl(self, data):
		# calc AGL per the barometer reading
		#    tello baro is assumed to be MSL in meters to two decimal places
		#    the elevation of Chiang Mai is 310 meters
		baro = int(data['baro'] * 100) # m to mm, float to int
		if not self.baro_base:
			self.baro_base = baro
		else:
			agl = baro - self.baro_base
			data['agl'] = max(agl,20) # minimum height is 20mm, camera above the ground
		return

class Video(threading.Thread):
	def __init__(self): # override
		self.stream = False
		self.state = 'init' # init, run, stop, crash
		self.hippocampus = False
		threading.Thread.__init__(self)

	def open(self):
		timestart = time.time()
		logging.info('start video capture')
		self.stream = cv.VideoCapture(video_url)  # takes about 5 seconds
		if not self.stream.isOpened():
			logging.error(f'Cannot open camera. abort. elapsed={time.time()-timestart}')
			self.state = 'crash'
			return False
		self.state = 'open'
		logging.info(f'video capture started, elapsed={time.time()-timestart}')

	def stop(self):
		self.state = 'stop'
	
	def run(self): # override
		# start hippocampus
		self.hippocampus = Hippocampus(True, True)
		self.hippocampus.start()
	
		logging.info(f'video thread started')
		self.state = 'run'
		while self.state == 'run': 
			# Capture frame-by-frame
			ret, frame = self.stream.read()
			if not ret:
				logging.error('Cannot receive frame.  Stream end?. Exiting.')
				self.state == 'crash'
				break
	
			# detect objects, build map, draw map
			ovec = self.hippocampus.processFrame(frame, 0)
			self.hippocampus.drawUI(frame)
	
			# Display the resulting frame
			if cv.waitKey(1) == ord('q'):
				self.state == 'stop'
		
		logging.info(f'video thread {self.state}')

		self.hippocampus.stop()

		if self.stream and self.stream.isOpened():
			self.stream.release()
			logging.info('video stream closed')

class Cmd:
	def __init__(self):
		self.state = 'init' # open, close
		self.sock = False
		self.timestamp = 0

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

	# send command and get return message. BLOCKING
	def sendCommand(self, cmd):
		# the takeoff command is way slow to return, with the tello hanging in the air, 
		# perhaps checking and calibrating itself before returning to the client
		timeout = cmd_sock_timeout
		if cmd == 'takeoff':
			timeout = cmd_takeoff_timeout
			self.sock.settimeout(timeout)

		# the command command sometimes returns a premature packet of bogus data.
		# it can be ignored
		retry = 1
		if cmd == 'command':
			retry = 3

		# rc command is fire and forget
		wait = True
		if 'rc' in cmd:
			wait = False

		# sending commands too quick evidently overwhelms the Tello
		diff = time.time() - self.timestamp
		if diff < cmd_time_btw_commands:
			logging.info(f'waiting {diff} between commands')
			time.sleep(diff)

		# send command and wait for response
		rmsg = 'error'
		timestart = time.time()
		try:
			logging.info(f'sendCommand {cmd} sendto')
			msg = cmd.encode(encoding="utf-8")
			len = self.sock.sendto(msg, cmd_address)
		except Exception as ex:
			logging.error(f'sendCommand {cmd} sendto failed:{str(ex)}, elapsed={time.time()-timestart}')
		else:
			logging.info(f'sendCommand {cmd} sendto complete, elapsed={time.time()-timestart}')
			if wait:
				for n in range(1,retry+1):
					logging.info(f'sendCommand {cmd} recfrom {n}')
					try:
						data, server = self.sock.recvfrom(cmd_maxlen)
					except Exception as ex:
						logging.error(f'sendCommand {cmd} {n} recvfrom failed: {str(ex)}, elapsed={time.time()-timestart}')
					else:
						# bogus data: b'\xcc\x18\x01\xb9\x88V\x00\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00I\x00\x00\xa7\x0f\x00\x06\x00\x00\x00\x00\x00W\xbe'
						if b'\xcc' in data:
							logging.info(f'sendCommand {cmd} {n} recvfrom returned bogus data, elapsed={time.time()-timestart}')
						else:
							try:
								rmsg = data.decode(encoding="utf-8")
							except Exception as ex:
								logging.error(f'sendCommand {cmd} {n} decode failed: {str(ex)}, elapsed={time.time()-timestart}')
							else:
								# success
								rmsg = rmsg.rstrip() # battery? returns string plus newline
								logging.info(f'sendCommand {cmd} {n} complete: {rmsg}, elapsed={time.time()-timestart}')
								if cmd == 'takeoff':
									self.sock.settimeout(cmd_sock_timeout)
								break; # for retry
		self.timestamp = time.time()
		return rmsg;

class Drone:
	def __init__(self):
		self.state = 'start', # start, ready, takeoff, airborne, land, down
		self.video = False
		self.telemetry = False
		self.cmd = False

	def prepareForTakeoff(self):
		logging.info('eyes starting ' + mode)
		timestart = time.time()
		
		# connect to tello
		wifi = Wifi(tello_ssid, retry=15)
		connected = wifi.connect()
		if not connected:
			return False
		
		# create three objects, one for each socket
		self.telemetry = Telemetry()
		self.video = Video()
		self.cmd = Cmd()

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
		logging.info('battery ok')

		# start video
		so = self.cmd.sendCommand("streamon")
		if so != 'ok':
			logging.error('tello streamon failed.  aborting.')
			return False

		# open video socket and start thread
		self.video.open() # blocks until started, about 5 seconds
		self.video.start()

		# ready for takeoff:
		#     command mode, good battery, video running, telemetry running, ui open
		self.state = 'ready'
		logging.info(f'ready for takeoff, elapsed {timestart-time.time()}')
		return True

	def wait(self):  # BLOCKING
		self.telemetry.join()
		self.video.join()

	def stop(self):
		if self.state == 'airborne':
			self.land()
		self.telemetry.stop()
		self.video.stop()
		self.cmd.close()
		logging.info('eyes shutdown')

	def do(self, cmd):
		if 'hover' in cmd:  # set hover position?, default nav? 
			pass
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
			'rc 10 10 10 10\n'  # left/right, forward/back, up/down, yaw; -100 to 100
			'height?\n'
			'tof?\n'
			'baro?'
	)
	demo = (
			'takeoff\n'
			'up 20\n'
			'cw 360\n'
			'right 20\n'
			'land'
	)
	testvideo = (
			'pause 15'
	)
	
	# run a mission
	def flyMission(s, drone):
		a = s.split('\n')
		for cmd in a:
			if 'pause' in cmd:
				logging.info(cmd)
				n = cmd.split(' ')[1]
				time.sleep(int(n))
			else:
				drone.do(cmd)

	def startLogging(filename):
		logging.basicConfig(
			format='%(asctime)s %(module)s %(levelname)s %(message)s', 
			filename=filename, 
			level=logging.DEBUG) # 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)  # console does not get DEBUG level
		logging.getLogger('').addHandler(console)
		logging.info('logging configured')

	logfolder = '/home/john/sk8/logs/'
	fname = f'{logfolder}/sk8_{datetime.now().strftime("%Y%m%d")}.log' # daily logfile
	startLogging(fname)
	drone = Drone()
	started = drone.prepareForTakeoff()
	if started:
		logging.info('start mission')
		flyMission(testheight, drone)

	drone.stop()
	drone.wait()
	
'''
'''
