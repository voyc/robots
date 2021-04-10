'''
tellomisson.py
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

# This program executes missions.  For example.
#      flyMission(demo)

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

# addresses
tello_ip = '192.168.10.1'
cmd_port = 8889  # may need to open firewall to these ports
tele_port = 8890
video_port = 11111

# UDP client socket to send and receive commands
cmdsock = False
cmdsock_timeout = 10 
cmd_address = (tello_ip, cmd_port)
cmd_maxlen = 1518

# UDP server socket to receive telemetry data
telemetrysock = False
telemetrysock_timeout = 10 
telemetry_address = ('',8890)
telemetry_maxlen = 1518 #?
telemetry_thread = False
telemetry_thread_status = 'init' # init, stopping, running
telemetry = {
	"pitch":-2,
	"roll":-2,
	"yaw":2,
	"vgx":0,
	"vgy":0,
	"vgz":0,
	"templ":62,
	"temph":65,
	"tof":6553,
	"h":0,
	"bat":42,
	"baro":404.45,
	"time":0,
	"agx":-37.00,
	"agy":48.00,
	"agz":-1008.00
}

# UDP server socket to receive video stream
video_stream = False
video_ip = 'udp://'+str(tello_ip)+':'+str(video_port)
video_ip = f'udp://{tello_ip}:{video_port}'
video_maxlen = 2**16
video_thread = False
video_thread_status = 'init' # init, stopping, running

# function to print string with timestamp
def log(s):
	tm = datetime.now().strftime("%H:%M:%S.%f")
	print(tm + ' ' + s)

# function to run a mission
def flyMission(s):
	a = s.split('\n')
	for cmd in a:
		if cmd[0:5] == 'sleep':
			log(cmd)
			n = cmd.split(' ')[1]
			time.sleep(int(n))
		else:
			sendCommand(cmd)

# function to send command and get return message
# The demo programs create a thread with a loop doing the recvfrom.  Why? Can the recvfrom block?
def sendCommand(cmd):
	global cmdsock,cmd_address
	rmsg = 'error'
	try:
		msg = cmd.encode(encoding="utf-8")
		len = cmdsock.sendto(msg, cmd_address)
	except Exception as ex:
		log ('sendCommand ' + cmd + ' sendto failed:'+str(ex))
	else:
		log('sendCommand ' + cmd)
		try:
			data, server = cmdsock.recvfrom(cmd_maxlen)
			rmsg = data.decode(encoding="utf-8")
		except Exception as ex:
			log ('sendCommand ' + cmd + ' recvfrom failed:'+str(ex))
			if cmd == 'command' and '0xcc' in str(ex):
				rmsg = 'ok' # ignore error ?
		else:
			log('sendCommand ' + cmd + ' : ' + rmsg)
	return rmsg;

# function to receive string of telemetry data
def telemetryLoop():
	global telemetry, telemetry_thread_status, telemetry_thread
	count = 0
	while True: 
		if telemetry_thread_status == 'stopping':
			break;
		try:
			data, server = telemetrysock.recvfrom(telemetry_maxlen)
		except Exception as ex:
			log ('Telemetry recvfrom failed: ' + str(ex))
			break
		count += 1
		storeTelemetry(data)
		if count%10 == 0:
			log(data.decode(encoding="utf-8"))

		# check battery and temperature
		#log('telemetry loop battery:' + str(telemetry['bat']) + ', high temperature:' + str(telemetry['temph']))
		print('.', end='')

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
	

# function to receive string of video data
def videoLoop():
	global video_stream, video_thread_status, video_thread
	count = 0

	video_stream = cv.VideoCapture(video_ip)

	if not video_stream.isOpened():
		print("Cannot open camera")
		stop()

	while True: 
		if video_thread_status == 'stopping':
			break;

		count += 1
		#if count%10 == 0:
		#	storeVideo(data)

		# Capture frame-by-frame
		ret, frame = video_stream.read()
		if not ret:
			print("Can't receive frame (stream end?). Exiting ...")
			video_thread_state == 'stopping'

		# Our operations on the frame come here
		#gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
		gray = frame

		# Display the resulting frame
		cv.imshow('frame', gray)
		if cv.waitKey(1) == ord('q'):
			video_thread_state == 'stopping'

	# When everything done, release the capture
	video_stream.release()
	cv.destroyAllWindows()

def dumpVideoBuffer(sock):
	log('dumping video buffer')
	while True:
		seg, addr = sock.recvfrom(video_maxlen)
		log('seg 0 ' + str(seg[0]))
		if struct.unpack("B", seg[0:1])[0] == 1:
			log("finish emptying buffer")
			break

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
	cmdsock.close()
	telemetrysock.close()
	if video_stream and video_stream.isOpened():
		video_stream.release()
	log ('eyes shutdown')
	quit()

# start
mode = 'prod'
for i, arg in enumerate(sys.argv):
	if arg == 'test':
		mode = 'test'
log ('eyes starting ' + mode)

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
		time.sleep(int(5))
		log('start mission')
		#flyMission(takeoffland)
		#flyMission(testheight)
		#flyMission(demo)
		flyMission(testvideo)
		log('mission complete')
		stopTelemetry()
		stopVideo()

# stop 
stop()
quit()


# # send user commands from keyboard
# while True: 
#     try:
#         msg = input("");
#         if not msg or 'quit' in msg:
#             break
#         msg = msg.encode(encoding="utf-8") 
#         sent = sock.sendto(msg, cmd_address)
#         log( sent);
#     except KeyboardInterrupt:
#         break

# function to receive string of video data
#https://github.com/dji-sdk/Tello-Python/blob/master/Tello_Video/tello.py
#import libh264decoder
#video_decoder = libh264decoder.H264Decoder()
#videosock = False
#videosock_timeout = 10 
#video_address = ('',11111)
#if videosock:
#	videosock.close()
#def videoLoopH264():
#	global video, video_thread_status, video_thread
#	count = 0
#	dat = b''
#	dumpVideoBuffer(videosock)
#	while True: 
#		if video_thread_status == 'stopping':
#			break;
#
#		try:
#	        	seg, addr = videosock.recvfrom(video_maxlen)
#		except Exception as ex:
#			log ('Video recvfrom failed: ' + str(ex))
#			break
#
#		count += 1
#		#if count%10 == 0:
#		#	storeVideo(data)
#
#		if struct.unpack("B", seg[0:1])[0] > 1:
#			dat += seg[1:]
#		else:
#			dat += seg[1:]
#			log('count ' + str(count))
#			log('len seg ' + str(len(seg)))
#			log('addr ' + str(addr))
#			#img = cv.imdecode(np.fromstring(dat, dtype=np.uint8), 1)
#			img = cv.imdecode(np.frombuffer(dat, dtype=np.uint8), 1)
#			cv.imshow('frame', img)
#			if cv.waitKey(1) & 0xFF == ord('q'):
#				#break
#				video_thread_state == 'stopping'
#			dat = b''
#
#	# When everything done, release the capture
#	cv.destroyAllWindows()
