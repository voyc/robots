' connectwifi.py - connect to a wifi hub'

import subprocess
import os
import time

class Wifi:
	def __init__(self, name, quiet=False):
		self.name = name
		self.quiet = quiet 
		self.retry = 10
		self.delay = 3
		self.original = ''

	def log(self, s):
		end = False if '...' in s else True
		if not self.quiet:
			if end:
				print(s)
			else:
				print(s,end='',flush=True)

	def connect(self, name=False):
		name = name or self.name
		self.original = self.get()
		if self.original == name:
			self.log(f'{name} already connected')
			return False 
		
		rc = False
		for n in range(self.retry):
			s = f"looking for {name}..." if n == 0 else '...'
			self.log(s)
			rc = self.find(name)
			if rc:
				break;
			time.sleep(self.delay)
		if rc:
			self.log('found')
		else:
			self.log(f'not found')
			return rc

		ret = False 
		for n in range(self.retry):
			s = f"connecting to {name}..." if n == 0 else '...'
			self.log(s)
			cmd = f'nmcli dev wifi connect {name}'
			try:
				s = subprocess.check_output(cmd, shell=True)
				ret = True
				break;
			except:
				pass
			time.sleep(self.delay)
		if ret:
			self.log(f'connected')
		else:
			self.log(f'failed')
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
