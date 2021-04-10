# eyes.py  models the tello drone

import socket
import threading
import cv2 as cv
import monad
import os
import subprocess

class Eyes:
	tello_ip = '192.168.10.1'  # tello controller is first device connected to the hub

	cmd_port = 8889  # may need to open firewall to these ports
	cmd_address = (tello_ip, cmd_port)
	cmd_maxlen = 1518
	cmd_timeout = 10

	tele_port = 8890  # telemetry
	tele_address = ('',tele_port)
	tele_maxlen = 1518 #?
	tele_timeout = 10

	video_port = 11111

	safe_battery = 20
	safe_temperature = 90

	def __init__(self):
		monad.log('eyes object created')
		self.tele_thread = None
		self.video_thread = None

	def connect(self):  # not used
		monad.log('eyes connecting')	
		ret = True
		cmd = 'nmcli dev wifi list --rescan yes'
		try:
			s = subprocess.check_output(cmd, shell=True)
		except:
			pass

		cmd = 'nmcli dev wifi connect TELLO-591FFC'
		try:
			s = subprocess.check_output(cmd, shell=True)
		except:
			ret = False

		monad.log(f'connect to Tello: {ret}')
		return ret

	def disconnect(self):  # not used
		rc = os.system('nmcli dev wifi disconnect TELLO_591FFC')

	def getConnection(self):
		cmd = 'nmcli -f IN-USE,SSID dev wifi list | grep \*'
		s = subprocess.check_output(cmd, shell=True)
		y = str(s)[4:len(str(s))-4].strip()
		return y

	def checkConnection(self):
		nw = self.getConnection()
		rc = nw[0:5] == 'TELLO'
		return rc

	def open(self):
		# open command socket
		self.startCmd()

		# start tello command processing
		rc = self.sendCommand('command', wait=True)
		if rc != 'ok':
			monad.log('tello command command failed')
			return False 

		# start tello streaming, video and telemetry
		rc = self.sendCommand('streamon', wait=True)
		if  rc != 'ok':
			monad.log('tello streamon command failed')
			return False

		# open sockets and start threads, to receive video and telemetry
		self.startTele()
		self.startVideo()

		monad.log('eyes connected')	
		return True

	def startTele(self):
		# UDP server socket to receive telemetry (tello is broadcasting on a client socket)
		self.tele_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.tele_sock.settimeout(self.tele_timeout)
		self.tele_sock.bind(self.tele_address)

		# thread to read the telemetry socket
		self.tele_thread = threading.Thread(target=self.teleLoop)
		self.tele_thread.start()
		monad.log('telemetry thread started')

	def teleLoop(self):
		global monad
		count = 0
		while True: 
			if monad.state == 'shutdown':
				break;  # thread stops on exit from this function
			try:
				data, server = self.tele_sock.recvfrom(self.tele_maxlen)
			except Exception as ex:
				monad.log('Telemetry recvfrom failed: ' + str(ex))
				monad.cortex.command('kill')
				continue
			count += 1
			self.storeTele(data)
			if count%10 == 0:
				monad.log(data.decode(encoding="utf-8"))
	
	def storeTele(self,data):
		# data=b'pitch:-2;roll:-2;yaw:2;vgx:0;vgy:0;vgz:0;templ:62;temph:65;
		#	tof:6553;h:0;bat:42;baro:404.45;time:0;agx:-37.00;agy:48.00;agz:-1008.00;'
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
		#monad.log(f'temph {monad.telem["temph"]}')
		
	def startVideo(self):
		self.video_thread = threading.Thread(target=self.videoLoop)
		self.video_thread.start()
		monad.log('video thread started')

	def videoLoop(self):
		global monad
		#cap = cv.VideoCapture('udp://'+self.tello_ip+':'+str(self.video_port))
		#if not cap.isOpened():
		#	monad.log("Cannot open camera")
		#	monad.cortex.command('kill')
		count = 0
		while True: 
			count += 1
			if monad.state == 'shutdown':
				break;  # thread stops
			#ret, frame = cap.read()  # ret=bool, frame=data
			#if not ret:
			#	monad.log("Cannot receive frame (stream end?). Exiting ...")
			#	monad.state - 'shutdown'
			#	break
			#gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

			##cv.imshow('frame', gray)
			##if cv.waitKey(1) == ord('q'):
			##	break
			
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
		monad.log('cmd socket open')

	def sendCommand(self,cmd, wait=False):
		global monad
		rmsg = ''
		try:
			msg = cmd.encode(encoding="utf-8")
			len = self.cmd_sock.sendto(msg, self.cmd_address)
			monad.log(f'command {cmd} sent')
		except Exception as ex:
			monad.log(cmd + ' sendto failed:'+str(ex))
			monad.cortex.command('kill')
		else:
			if wait:
				try:
					data, server = self.cmd_sock.recvfrom(self.cmd_maxlen) # blocking
					print(f'data: {data}')
					print(f'server: {server}')
					# why do we get this sometimes
					# data: b'\xcc\x18\x01\xb9\x88V\x00\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00I\x00\x00\xa7\x0f\x00\x06\x00\x00\x00\x00\x00W\xbe'
					rmsg = data.decode(encoding='utf-8')
				except Exception as ex:
					monad.log(cmd + ' recvfrom failed:'+str(ex))
					monad.cortex.command('kill')
				else:
					monad.log(cmd + ' : ' + rmsg)
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
		if int(temp) > self.safe_temperature:
			tempok = False
		return tempok

	def start(self):
		pass
	def stop(self):
		pass
	def resume(self):
		pass
	def home(self):
		pass
	def kill(self):
		pass

