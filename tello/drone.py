'''
drone.py - class Drone, drive the tello drone

connect to all three sockets
fly one or more missions
quit,  no loop
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
from hippocampus import Hippocampus
from wifi import Wifi

class Drone:
	def __init__(self):
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
		self.cmd_retry = 3
		self.cmd_takeoff_timeout = 20  # seconds
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
		self.telemetry_baro_start = 0
		self.telemetry_height = 0

		# UDP server socket to receive video stream
		self.video_stream = False
		self.video_maxlen = 2**16
		self.video_thread = False
		self.video_thread_status = 'init' # init, stopping, running

	# send command and get return message. nb, this command blocks.
	def sendCommand(self, cmd, retry=False):   # , timeout=0.1, wait=True, callback=None):
		retry = retry or self.cmd_retry
		rmsg = 'error'
		diff = time.time() - self.cmd_timestamp
		if diff < self.cmd_time_btw_commands:
			log(f'waiting {diff} between commands')
			time.sleep(diff)
		timestart = time.time()
		try:
			msg = cmd.encode(encoding="utf-8")
			len = self.cmd_sock.sendto(msg, self.cmd_address)
		except Exception as ex:
			log ('sendCommand ' + cmd + ' sendto failed:'+str(ex))
		else:
			for n in range(1,retry+1):
				log(f'sendCommand {cmd} {n}')
				try:
					data, server = self.cmd_sock.recvfrom(self.cmd_maxlen)
				except Exception as ex:
					log (f'sendCommand {cmd} {n} recvfrom failed: {str(ex)}')
				else:
					# bogus data: b'\xcc\x18\x01\xb9\x88V\x00\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00I\x00\x00\xa7\x0f\x00\x06\x00\x00\x00\x00\x00W\xbe'
					if b'\xcc' in data:
						log (f'sendCommand {cmd} {n} recvfrom returned bogus data')
					else:
						try:
							rmsg = data.decode(encoding="utf-8")
						except Exception as ex:
							log (f'sendCommand {cmd} {n} decode failed: {str(ex)}')
						else:
							timeend = time.time()
							timeprocess = timeend - timestart
							log (f'sendCommand {cmd} {n}: {rmsg} {timeprocess}')
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
				log ('Telemetry recvfrom failed: ' + str(ex))
				break
			data = data.strip()
			self.storeTelemetry(data)
	
			# log
			count += 1
			if count >= self.telemetry_log_nth:
				count = 0
				log(data.decode(encoding="utf-8"))
	
			# get camera height using barometer reading
			baro = self.telemetry_data['baro']
			if not self.telemetry_baro_start:
				self.telemetry_baro_start = baro
			baro = baro - self.telemetry_baro_start
			baro = max(baro,0)
			self.telemetry_height = round(baro * 10, 1) # cm to mm

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
		count = 0
	
		log('start video capture')
		self.video_stream = cv.VideoCapture(self.video_url)  # takes about 5 seconds
		log('video capture started')
	
		if not self.video_stream.isOpened():
			log("Cannot open camera")
			self.stop()
	
		hippocampus = Hippocampus(True, True)
		hippocampus.start()
	
		while True: 
			if self.video_thread_status == 'stopping':
				break;
	
			count += 1
			#if count%10 == 0:
			#	storeVideo(data)
	
			# Capture frame-by-frame
			ret, frame = self.video_stream.read()
			if not ret:
				log("Can't receive frame (stream end?). Exiting ...")
				self.video_thread_state == 'stopping'
	
			# detect objects, build map, draw map
			hippocampus.camera_height = self.telemetry_height
			hippocampus.processFrame(frame)
			hippocampus.drawUI(frame)
	
			# Display the resulting frame
			#cv.imshow('frame', frame) - let this be done by hippocampus
			if cv.waitKey(1) == ord('q'):
				self.video_thread_state == 'stopping'
	
		# When everything done, release the capture
		self.video_stream.release()
		cv.destroyAllWindows()
		hippocampus.stop()
	
	def startVideo(self):
		self.video_thread = threading.Thread(target=self.videoLoop)
		self.video_thread.start()
		self.video_thread_status = 'running'
	
	def stopVideo(self):
		if self.video_thread_status == 'running':
			self.video_thread_status = 'stopping'
			self.video_thread.join()
			
	def stop(self):
		self.stopTelemetry()
		self.stopVideo()
		self.cmd_sock.close()
		self.telemetry_sock.close()
		if self.video_stream and self.video_stream.isOpened():
			self.video_stream.release()
		log ('eyes shutdown')
		quit()

	def start(self):
		mode = 'prod'
		for i, arg in enumerate(sys.argv):
			if arg == 'test':
				mode = 'test'
		log ('eyes starting ' + mode)
		
		# connect to tello
		wifi = Wifi(self.tello_ssid)
		connected = wifi.connect()
		if not connected:
			quit()
		
		# Create cmd socket as UDP client
		self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.cmd_sock.settimeout(self.cmd_sock_timeout)
		#sock.bind(locaddr) # bind is for server ???
		log('cmd_sock open')
		
		# Create telemetry socket as UDP server
		self.telemetry_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.telemetry_sock.settimeout(self.telemetry_sock_timeout)
		self.telemetry_sock.bind(self.telemetry_address) # bind is for server, not client
		log('telemetry_sock open')
		
		# send the "command" command to start receiving the data stream
		cmd = self.sendCommand("command")
		if cmd == 'ok':
			batt = self.sendCommand("battery?")
			if int(batt) < 20:
				log('battery low.  aborting.')
			else:
				self.startTelemetry() 
				so = self.sendCommand("streamon")
				time.sleep(int(5))
				self.startVideo()
				time.sleep(int(5)) # wait until video started


# print timestamp and string to console
def log(s):
	tm = datetime.now().strftime("%H:%M:%S.%f")
	print(tm + ' ' + s)

if __name__ == '__main__':
	# missions
	takeoffland = (
			'takeoff\n'
			'sleep 3\n'
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
	def flyMission(s):
		a = s.split('\n')
		for cmd in a:
			if cmd[0:5] == 'sleep':
				log(cmd)
				n = cmd.split(' ')[1]
				time.sleep(int(n))
			else:
				self.sendCommand(cmd)

	drone = Drone()
	drone.start()
	log('start mission')
	#flyMission(takeoffland)
	#flyMission(testheight)
	#flyMission(demo)
	flyMission(testvideo)
	log('mission complete')
	drone.stop()
