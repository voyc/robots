'wifi.py - connect to a wifi hub'

import subprocess
import os
import time
import logging

class Wifi:
	def __init__(self, name, quiet=False):
		self.name = name
		self.quiet = quiet 
		self.retry = 10
		self.delay = 3
		self.original = ''

	def connect(self, name=False):
		name = name or self.name
		self.original = self.get()
		if self.original == name:
			logging.info(f'{name} already connected')
			return True 
		
		timestart = time.time()
		rc = False
		for n in range(1,self.retry+1):
			logging.info(f'looking for {name} {n}')
			rc = self.find(name)
			if rc:
				break;
			time.sleep(self.delay)
		if rc:
			logging.info(f'{name} found, elapsed={time.time()-timestart}')
		else:
			logging.info(f'{name} not found')
			return rc

		timestart = time.time()
		ret = False 
		for n in range(1,self.retry+1):
			logging.info(f'connecting to {name} {n}')
			cmd = f'nmcli dev wifi connect {name}'
			try:
				s = subprocess.check_output(cmd, shell=True)
				ret = True
				break;
			except:
				pass
			time.sleep(self.delay)
		if ret:
			logging.info(f'{name} connected, elapsed={time.time()-timestart}')
		else:
			logging.info(f'{name} connection failed')
		return ret

	def restore(self):
		if self.original:
			self.connect(self.original)

	def find(self, name):
		cmd = 'nmcli -f SSID dev wifi list'
		s = subprocess.check_output(cmd, shell=True)
		y = bytes(name, 'utf-8') in s
		return y

	def get(self):
		cmd = 'nmcli -f IN-USE,SSID dev wifi list | grep \*'
		s = subprocess.check_output(cmd, shell=True)
		y = str(s)[4:len(str(s))-4].strip()
		return y

	def check(self):
		nw = self.get()
		rc = nw == self.name
		return rc

if __name__ == '__main__':
	wifi = Wifi('TELLO-591FFC')
	print(wifi.check())
	print(wifi.get())
	print(wifi.connect())
	print(wifi.connect('JASMINE'))
