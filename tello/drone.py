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
		
		# UDP client socket to send and receive commands
		self.cmdsock = False
		self.cmdsock_timeout = 7 # seconds
		self.cmd_retry = 3
		self.cmd_takeoff_timeout = 20  # seconds
		self.cmd_time_btw_commands = 0.1  # seconds.  Commands too quick => Tello not respond.
		self.cmd_address = (tello_ip, cmd_port)
		self.cmd_maxlen = 1518
		self.cmd_timestamp = 0
		
		# UDP server socket to receive telemetry data
		self.telemetrysock = False
		self.telemetrysock_timeout = 10 
		self.telemetry_address = ('',8890)
		self.telemetry_maxlen = 1518 #?
		self.telemetry_thread = False
		self.telemetry_thread_status = 'init' # init, stopping, running
		self.telemetry = {
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
		self.start_baro = 0
		self.height = 0
		self.quiet = False

		# UDP server socket to receive video stream
		self.video_stream = False
		self.video_ip = f'udp://{tello_ip}:{video_port}'
		self.video_maxlen = 2**16
		self.video_thread = False
		self.video_thread_status = 'init' # init, stopping, running

	# send command and get return message. nb, this command blocks.
	def sendCommand(cmd, retry=cmd_retry):   # , timeout=0.1, wait=True, callback=None):
		global cmdsock,cmd_address,cmd_timestamp
		rmsg = 'error'
		diff = time.time() - cmd_timestamp
		if diff < cmd_time_btw_commands:
			log(f'waiting {diff} between commands')
			time.sleep(diff)
		timestart = time.time()
		try:
			msg = cmd.encode(encoding="utf-8")
			len = cmdsock.sendto(msg, cmd_address)
		except Exception as ex:
			log ('sendCommand ' + cmd + ' sendto failed:'+str(ex))
		else:
			for n in range(1,retry+1):
				log(f'sendCommand {cmd} {n}')
				try:
					data, server = cmdsock.recvfrom(cmd_maxlen)
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
		cmd_timestamp = time.time()
		return rmsg;

	# thread target function to receive string of telemetry data
	def telemetryLoop():
		global telemetry, telemetry_thread_status, telemetry_thread, start_baro
		count = 0
		while True: 
			if telemetry_thread_status == 'stopping':
				break;
			try:
				data, server = telemetrysock.recvfrom(telemetry_maxlen)
			except Exception as ex:
				log ('Telemetry recvfrom failed: ' + str(ex))
				break
			data = data.strip()
			storeTelemetry(data)
	
			# log
			count += 1
			if count >= telemetry_log_nth:
				count = 0
				log(data.decode(encoding="utf-8"))
	
			# get camera height using barometer reading
			baro = telemetry['baro']
			if not start_baro:
				start_baro = baro
			baro = baro - start_baro
			baro = max(baro,0)
			height = round(baro * 10, 1) # cm to mm

	def startTelemetry():
		global telemetry_thread_status, telemetry_thread
		telemetry_thread = threading.Thread(target=telemetryLoop)
		telemetry_thread.start()
		telemetry_thread_status = 'running'
	
	def stopTelemetry():
		global telemetry_thread_status, telemetry_thread
		if telemetry_thread_status == 'running':
			telemetry_thread_status = 'stopping'
			telemetry_thread.join()
			
	def storeTelemetry(data):
		# data=b'pitch:-2;roll:-2;yaw:2;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:6553;h:0;bat:42;baro:404.45;time:0;agx:-37.00;agy:48.00;agz:-1008.00;'
		global telemetry
		sdata = data.decode('utf-8')
		adata = sdata.split(';')
		for stat in adata:
			if len(stat) <= 2: # last item is cr+lf
				break
			name,value = stat.split(':')
			if name in ['baro','agx','agy','agz']:
				telemetry[name] = float(value);
			else:
				telemetry[name] = int(value);
	
	# thread target function to receive string of video data
	def videoLoop():
		global video_stream, video_thread_status, video_thread
		count = 0
	
		log('start video capture')
		video_stream = cv.VideoCapture(video_ip)  # takes about 5 seconds
		log('video capture started')
	
		if not video_stream.isOpened():
			log("Cannot open camera")
			stop()
	
		hippocampus = Hippocampus(True, True)
		hippocampus.start()
	
		while True: 
			if video_thread_status == 'stopping':
				break;
	
			count += 1
			#if count%10 == 0:
			#	storeVideo(data)
	
			# Capture frame-by-frame
			ret, frame = video_stream.read()
			if not ret:
				log("Can't receive frame (stream end?). Exiting ...")
				video_thread_state == 'stopping'
	
			# detect objects, build map, draw map
			hippocampus.camera_height = height
			hippocampus.processFrame(frame)
			hippocampus.drawUI(frame)
	
			# Display the resulting frame
			#cv.imshow('frame', frame) - let this be done by hippocampus
			if cv.waitKey(1) == ord('q'):
				video_thread_state == 'stopping'
	
		# When everything done, release the capture
		video_stream.release()
		cv.destroyAllWindows()
		hippocampus.stop()
	
	def startVideo():
		global video_thread_status, video_thread
		video_thread = threading.Thread(target=videoLoop)
		video_thread.start()
		video_thread_status = 'running'
	
	def stopVideo():
		global video_thread_status, video_thread
		if video_thread_status == 'running':
			video_thread_status = 'stopping'
			video_thread.join()
			
	def stop():
		stopTelemetry()
		stopVideo()
		cmdsock.close()
		telemetrysock.close()
		if video_stream and video_stream.isOpened():
			video_stream.release()
		log ('eyes shutdown')
		quit()

	def start():
		mode = 'prod'
		for i, arg in enumerate(sys.argv):
			if arg == 'test':
				mode = 'test'
		log ('eyes starting ' + mode)
		
		# connect to tello
		wifi = Wifi(tello_ssid)
		connected = wifi.connect()
		if not connected:
			quit()
		
		# Create cmd socket as UDP client
		cmdsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		cmdsock.settimeout(cmdsock_timeout)
		#sock.bind(locaddr) # bind is for server ???
		log('cmdsock open')
		
		# Create telemetry socket as UDP server
		telemetrysock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		telemetrysock.settimeout(telemetrysock_timeout)
		telemetrysock.bind(telemetry_address) # bind is for server, not client
		log('telemetrysock open')
		
		# Create video socket as UDP server
		#videosock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		#videosock.settimeout(videosock_timeout)
		#videosock.bind(video_address) # bind is for server, not client
		#log('videosock open')
		
		# send the "command" command to start receiving the data stream
		cmd = sendCommand("command")
		if cmd == 'ok':
			batt = sendCommand("battery?")
			if int(batt) < 20:
				log('battery low.  aborting.')
			else:
				startTelemetry() 
				so = sendCommand("streamon")
				time.sleep(int(5))
				startVideo()
				time.sleep(int(5)) # wait until video started


# print timestamp and string to console
quiet = False
def log(s):
	if not quiet:
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
				sendCommand(cmd)

	drone = Drone()
	drone.start()
	log('start mission')
	#flyMission(takeoffland)
	#flyMission(testheight)
	#flyMission(demo)
	flyMission(testvideo)
	log('mission complete')
	drone.stop()
