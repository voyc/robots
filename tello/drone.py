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

class Drone:
	def __init__(self):
		self.state = 'start', # start, ready, airborne, down

		# addresses
		self.tello_ssid = 'TELLO-591FFC'
		self.tello_ip = '192.168.10.1'
		self.cmd_port = 8889  # may need to open firewall to these ports
		self.tele_port = 8890
		self.video_port = 11111
		self.video_url = f'udp://{self.tello_ip}:{self.video_port}'
		
		# UDP client socket to send and receive commands
		self.cmd_sock = False
		self.cmd_sock_timeout = 7 # seconds
		self.cmd_takeoff_timeout = 20  # seconds. takeoff slow to return
		self.cmd_time_btw_commands = 0.1  # seconds.  Commands too quick => Tello not respond.
		self.cmd_address = (self.tello_ip, self.cmd_port)
		self.cmd_maxlen = 1518
		self.cmd_timestamp = 0
		
		# UDP server socket to receive telemetry data
		self.telemetry_sock = False
		self.telemetry_sock_timeout = 10 
		self.telemetry_address = ('',self.tele_port)
		self.telemetry_maxlen = 1518 #?
		self.telemetry_thread = False
		self.telemetry_thread_status = 'init' # init, stopping, running
		self.telemetry_data = {
			"pitch":-2,
			"roll":-2,
			"yaw":2,
			"vgx":0,
			"vgy":0,
			"vgz":0,
			"templ":62,
			"temph":65,
			"tof":6553,       # height in cm, time of flight, typical range 10 to 56
			"h":0,            # height in cm, always 0
			"bat":42,
			"baro":404.45,    # height in cm, range 322.41 to 323.34 or 321.53 to 322.11
			"time":0,
			"agx":-37.00,
			"agy":48.00,
			"agz":-1008.00
		}
		self.telemetry_log_nth = 60
		self.baro_start = 0
		self.baro_temp_array = [] # used onetime to average start value 
		self.baro_height = 0

		# UDP server socket to receive video stream
		self.video_stream = False
		self.video_maxlen = 2**16
		self.video_thread = False
		self.video_thread_status = 'init' # init, stopping, running

	# send command and get return message. nb, this command blocks.
	def sendCommand(self, cmd):
		# the takeoff command is way slow to return, with the tello hanging in the air, 
		# perhaps checking and calibrating itself before returning to the client
		timeout = self.cmd_sock_timeout
		if cmd == 'takeoff':
			timeout = self.cmd_takeoff_timeout
			self.cmd_sock.settimeout(timeout)

		# the command command sometimes returns a premature packet of bogus data.
		# it can be ignored
		retry = 1
		if cmd == 'command':
			retry = 3

		# sending commands too quick evidently overwhelms the Tello
		diff = time.time() - self.cmd_timestamp
		if diff < self.cmd_time_btw_commands:
			logging.info(f'waiting {diff} between commands')
			time.sleep(diff)

		# send command and wait for response
		rmsg = 'error'
		logging.info(f'sendCommand {cmd} sendto')
		timestart = time.time()
		try:
			msg = cmd.encode(encoding="utf-8")
			len = self.cmd_sock.sendto(msg, self.cmd_address)
		except Exception as ex:
			logging.error(f'sendCommand {cmd} sendto failed:{str(ex)}, elapsed={time.time()-timestart}')
		else:
			logging.info(f'sendCommand {cmd} sendto complete, elapsed={time.time()-timestart}')
			for n in range(1,retry+1):
				logging.info(f'sendCommand {cmd} recfrom {n}')
				try:
					data, server = self.cmd_sock.recvfrom(self.cmd_maxlen)
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
								self.state = 'takeoff'
								timeout = self.cmd_sock_timeout
								self.cmd_sock.settimeout(timeout)
							if cmd == 'land':
								self.state = 'down'
							break; # while true loop, success
		self.cmd_timestamp = time.time()
		return rmsg;

	# thread target function to receive string of telemetry data
	def telemetryLoop(self):
		count = 0
		while True: 
			if self.telemetry_thread_status == 'stopping':
				break;
			try:
				data, server = self.telemetry_sock.recvfrom(self.telemetry_maxlen)
			except Exception as ex:
				logging.error('Telemetry recvfrom failed: ' + str(ex))
				break
			data = data.strip()
			self.storeTelemetry(data)
	
			# log
			count += 1
			if count >= self.telemetry_log_nth:
				count = 0
				logging.debug(data.decode(encoding="utf-8"))
	
			# calc height per the barometer reading
			#    tello baro is assumed to be MSL in meters to two decimal places
			#    the elevation of Chiang Mai is 310 meters
			baro = int(round(self.telemetry_data['baro'] * 100)) # m to mm, float to int
			if not self.baro_start:
				if not self.state == 'ready':
					self.baro_temp_array.append(baro)
				else:
					self.baro_start = int(round(sum(baro_temp_array) / len(baro_temp_array)))
			else:
				baro = baro - self.baro_start
				baro = max(baro,20) # minimum height is 20mm, camera above the ground
				self.baro_height = baro

	def startTelemetry(self):
		self.telemetry_thread = threading.Thread(target=self.telemetryLoop)
		self.telemetry_thread.start()
		self.telemetry_thread_status = 'running'
	
	def stopTelemetry(self):
		if self.telemetry_thread_status == 'running':
			self.telemetry_thread_status = 'stopping'
			self.telemetry_thread.join()
			
	def storeTelemetry(self, data):
		# data=b'pitch:-2;roll:-2;yaw:2;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:6553;h:0;bat:42;baro:404.45;time:0;agx:-37.00;agy:48.00;agz:-1008.00;'
		sdata = data.decode('utf-8')
		adata = sdata.split(';')
		for stat in adata:
			if len(stat) <= 2: # last item is cr+lf
				break
			name,value = stat.split(':')
			if name in ['baro','agx','agy','agz']:
				self.telemetry_data[name] = float(value);
			else:
				self.telemetry_data[name] = int(value);
	
	# thread target function to receive string of video data
	def videoLoop(self):
		while True: 
			if self.video_thread_status == 'stopping':
				break;
	
			# Capture frame-by-frame
			ret, frame = self.video_stream.read()
			if not ret:
				logging.error('Cannot receive frame.  Stream end?. Exiting.')
				self.video_thread_status == 'stopping'
	
			# detect objects, build map, draw map
			hippocampus.camera_height = self.baro_height
			hippocampus.processFrame(frame, self.baro_height)
			hippocampus.drawUI(frame)
	
			# Display the resulting frame
			if cv.waitKey(1) == ord('q'):
				self.video_thread_status == 'stopping'
	
		self.stopVideo()
	
	def startVideo(self):
		# openvideo
		timestart = time.time()
		logging.info('start video capture')
		self.video_stream = cv.VideoCapture(self.video_url)  # takes about 5 seconds
		logging.info(f'video capture started, elapsed={time.time()-timestart}')
		if not self.video_stream.isOpened():
			logging.error("Cannot open camera")
			self.stop()
	
		# start hippocampus
		hippocampus = Hippocampus(True, True)
		hippocampus.start()
	
		# start the thread
		self.video_thread = threading.Thread(target=self.videoLoop)
		self.video_thread.start()
		self.video_thread_status = 'running'
	
	def stopVideo(self):
		# stop thread
		if self.video_thread_status == 'running':
			self.video_thread_status = 'stopping'
			self.video_thread.join()

			# stop hippocampus
			hippocampus.stop()

			# closeVideo
			if self.video_stream and self.video_stream.isOpened():
				self.video_stream.release()
			cv.destroyAllWindows()

	def stop(self):
		self.stopTelemetry()
		self.stopVideo()
		self.cmd_sock.close()
		self.telemetry_sock.close()
		logging.info('eyes shutdown')

	def start(self):
		# look for startup options
		mode = 'prod'
		for i, arg in enumerate(sys.argv):
			if arg == 'test':
				mode = 'test'

		logging.info('eyes starting ' + mode)
		timestart = time.time()
		
		# connect to tello
		wifi = Wifi(self.tello_ssid)
		connected = wifi.connect()
		if not connected:
			return False
		
		# Create cmd socket as UDP client (no bind)
		self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.cmd_sock.settimeout(self.cmd_sock_timeout)
		logging.info('cmd_sock open')
		
		# Create telemetry socket as UDP server
		self.telemetry_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.telemetry_sock.settimeout(self.telemetry_sock_timeout)
		self.telemetry_sock.bind(self.telemetry_address) # bind is for server, not client
		logging.info('telemetry_sock open')
		
		# send the "command" command to start receiving the data stream
		cmd = self.sendCommand("command")
		if cmd == 'ok':
			batt = self.sendCommand("battery?")
			if int(batt) < 20:
				logging.error('battery low.  aborting.')
				return False
			else:
				self.startTelemetry() 
				so = self.sendCommand("streamon")
				self.startVideo() # blocks until started, about 5 seconds
		logging.info(f'ready for takeoff, elapsed {timestart-time.time()}')
		self.state = 'ready'
		return True # command on, good battery, video running, telemetry running, ui open

if __name__ == '__main__':
	# missions
	takeoffland = (
			'takeoff\n'
			'land'
	)
	testheight = (
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
			'sleep 15'
	)
	
	# run a mission
	def flyMission(s, drone):
		a = s.split('\n')
		for cmd in a:
			if cmd[0:5] == 'sleep':
				logging.info(cmd)
				n = cmd.split(' ')[1]
				time.sleep(int(n))
			else:
				drone.sendCommand(cmd)

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
	started = drone.start()
	if started:
		logging.info('start mission')
