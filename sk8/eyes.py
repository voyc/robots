# eyes.py  models the tello drone

import socket
import threading
import cv2 as cv
import monad

class Eyes:
	def __init__(self):
		print('eyes starting')	
		# test: cap = cv.VideoCapture('udp://'+str(tello_ip)+':'+str(video_port))

		# tello defined
		self.tello_admin_ip = '192.168.1.1'  # ???  config console of tello wifi hub
		self.tello_ip = '192.168.10.1'  # tello controller is first device connected to the hub
		self.cmd_port = 8889  # may need to open firewall to these ports
		self.tele_port = 8890  # telemetry
		self.video_port = 11111
		self.cmd_maxlen = 1518
		self.tele_maxlen = 1518 #?
		self.videe_maxlen = 1518 #?
		self.safe_battery = 20
		self.safe_temparature = 25

		self.cmd_address = (self.tello_ip, self.cmd_port)
		self.tele_address = ('',self.tele_port)
		self.video_address = ('',self.video_port)

		# config
		self.cmd_timeout = 10
		self.tele_timeout = 10
		self.video_timeout = 10

		# start all threads immediately. execution controlled by global state
		self.startCmd()
		self.startTele()
		self.startVideo()

		rc = self.sendCommand('command', wait=True)
		if rc != 'ok':
			print('tello command command failed')
		rc = self.sendCommand('streamon', wait=True)
		if  rc != 'ok':
			print('tello streamon command failed')
		print('eyes started')	

	def startTele(self):
		# UDP server socket to receive telemetry (tello is broadcasting on a client socket)
		self.tele_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.tele_sock.settimeout(self.tele_timeout)
		self.tele_sock.bind(self.tele_address)

		# thread to read the telemetry socket
		self.tele_thread = threading.Thread(target=self.teleLoop)
		self.tele_thread.start()
		print('telemetry thread started')

	def teleLoop(self):
		global monad
		count = 0
		while True: 
			if monad.state == 'shutdown':
				break;  # thread stops on exit from this function
			try:
				data, server = self.tele_sock.recvfrom(self.tele_maxlen)
			except Exception as ex:
				print('Telemetry recvfrom failed: ' + str(ex))
				monad.state = 'shutdown'
				break
			count += 1
			self.storeTele(data)
			if count%10 == 0:
				print(data.decode(encoding="utf-8"))
	
			# check battery and temperature
			print('battery:' + str(monad.telem['bat']) + ', high temperature:' + str(monad.telem['temph']))
	
	def storeTele(self,data):
		# data=b'pitch:-2;roll:-2;yaw:2;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:6553;h:0;bat:42;baro:404.45;time:0;agx:-37.00;agy:48.00;agz:-1008.00;'
		global monad
		sdata = data.decode('utf-8')
		adata = sdata.split(';')
		for stat in adata:
			if len(stat) <= 2: # last item is cr+lf
				break
			name,value = stat.split(':')
			if name in ['baro','agx','agy','agz']:
				monad.telem[name] = float(value);
			else:
				monad.telem[name] = int(value);
		

	def startVideo(self):
		# UDP server socket to receive video (tello is broadcasting on a client socket)
		self.video_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.video_sock.settimeout(self.video_timeout)
		self.video_sock.bind(self.video_address)

		# thread to read the videometry socket
		self.video_thread = threading.Thread(target=self.videoLoop)
		self.video_thread.start()
		print('video thread started')

	def videoLoop(self):
		global monad
		cap = cv.VideoCapture('udp://'+self.tello_ip+':'+str(self.video_port))
		if not cap.isOpened():
			print("Cannot open camera")
			monad.state = 'shutdown'
			return
		count = 1
		while True: 
			if monad.state == 'shutdown':
				break;  # thread stops
			count += 1
			# Capture frame-by-frame
			ret, frame = cap.read()
			# if frame is read correctly ret is True
			if not ret:
				print("Cannot receive frame (stream end?). Exiting ...")
				monad.state - 'shutdown'
				break
			# Our operations on the frame come here
			gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
			# Display the resulting frame
			#cv.imshow('frame', gray)
			#if cv.waitKey(1) == ord('q'):
			#	break
			# When everything done, release the capture
			
			self.processFrame()
			self.updateMap()
		cap.release()
		#cv.destroyAllWindows()

	def processFrame(self):
		pass

	def updateMap(self):
		pass

	def startCmd(self):
		# UDP client socket to send and receive commands
		self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.cmd_sock.settimeout(self.cmd_timeout)
		print('cmd socket open')

	def sendCommand(self,cmd, wait=False):
		global monad
		rmsg = ''
		try:
			msg = cmd.encode(encoding="utf-8")
			len = self.cmd_sock.sendto(msg, self.cmd_address)
			print(f'command {cmd} sent')
		except Exception as ex:
			print(cmd + ' sendto failed:'+str(ex))
			monad.state = 'shutdown'
		else:
			if wait:
				try:
					data, server = self.cmd_sock.recvfrom(self.cmd_maxlen) # blocking
					rmsg = data.decode(encoding="utf-8")
				except Exception as ex:
					print(cmd + ' recvfrom failed:'+str(ex))
					monad.state = 'shutdown'
				else:
					print(cmd + ' : ' + rmsg)
		return rmsg;

	def checkBattery(self):
		bat = 100
		batok = True
		if 'bat' in monad.telem:
			bat = monad.telem['bat']
		if int(bat) < self.safe_battery:
			batok = False
		return batok

	def checkTemperature(self):
		temp = 2
		tempok = True
		if 'temph' in monad.telem:
			temp = monad.telem['temph']
		if int(temp) > self.safe_battery:
			tempok = false
		return tempok

