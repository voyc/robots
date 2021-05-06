'''
universal.py - global constants and functions
'''

import datetime
import os 
import logging

dirbase = 'home/john/sk8'
dirday  = f'{datetime.datetime.now().strftime("%Y%m%d")}'
dirtime = f'{datetime.datetime.now().strftime("%H%M%S")}'
def makedir(form): 
	s = f'/{dirbase}/{dirday}/{dirtime}/{form}'
	os.makedirs(s, exist_ok=True)
	return s

max_mmo = 200 # maximum mm offset
max_vel = 60 # maximum safe velocity (up to 100)

def configureLogging():
	# factory: 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL
	logging.MISSION = 15
	logging.DEBUG = 17

	debug_format = '%(asctime)s %(levelno)s %(module)s %(message)s' 
	debug_fname = f"{makedir('log')}/debug.log"
	mission_fname = f"{makedir('log')}/mission.log"

	# root log level
	logger = logging.getLogger('')
	logger.setLevel(logging.MISSION)

	# log 1: console
	console_handler = logging.StreamHandler()
	console_handler.setLevel(logging.INFO)  # console gets info and above, no formatting
	logger.addHandler(console_handler)

	# log 2: debug
	debug_handler = logging.FileHandler(debug_fname)
	debug_handler.setLevel(10)
	debug_handler.setFormatter( logging.Formatter(debug_format))
	logger.addHandler(debug_handler)

	# log 3: mission
	mission_handler = logging.FileHandler(mission_fname)
	class MissionFilter(logging.Filter):
		def filter(self, record):
			return record.levelno == logging.MISSION
	mission_handler.addFilter( MissionFilter())
	mission_handler.setLevel(logging.MISSION)
	logger.addHandler(mission_handler)

	logging.info('logging configured')

def composeRcCommand(ovec): # compose tello rc command
	x,y,z,w = ovec # input orientation vector in mm, diff between frameMap and baseMap

	# output rc cmd string, 'rc x y z w'
	# each param is -100 to 100, as pct of full velocity
	# x:left/right roll, y:back/forward pitch, z:down/up, w:ccw/cw yaw as angular velocity


	# if we're off by 30cm or more, land
	if abs(x) > max_mmo or abs(y) > max_mmo:
		return 'land'

	# interpolate to safe velocity range
	x = int((x/(max_mmo*2))*(max_vel*2))
	y = int((y/(max_mmo*2))*(max_vel*2))

	s = f'rc {x} {y} {z} {w}'
	return s

if __name__ == '__main__':
	framenum = 1
	print(f"{makedir('frame')}/{framenum}.jpg")
	framenum += 1
	print(f"{makedir('frame')}/{framenum}.jpg")
	print(f"{makedir('train')}/{framenum}.txt")
	print(f"{makedir('log')}/debug.log")
	configureLogging()

	s = composeRcCommand((30,40,16,25))	
	print(s)

	logging.log(logging.MISSION, 'test mission log')
	logging.debug('test debug log')
	logging.info('test info log')
