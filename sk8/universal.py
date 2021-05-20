''' universal.py - global constants and functions '''

import datetime
import os 
import logging
import time

clsNone = -1
clsCone = 0
clsPadl = 1
clsPadr = 2
clsSpot = 3

dirhome = '/home/john/sk8'
sday   = f'{datetime.datetime.now().strftime("%Y%m%d")}'
stime  = f'{datetime.datetime.now().strftime("%H%M%S")}'
dirbase = False
dirmode = 'fly'

mission_start = time.time()

def makedir(form=''): 
	if not dirbase:
		print('programmer error - logging not configured')
		return
	form = f'/{form}' if form else ''
	s = f'{dirbase}/{sday}/{stime}/{form}'
	if not form:
		s = s[:len(s)-1]  # truncate extra slash
	os.makedirs(s, exist_ok=True)
	return s

def configureLogging(mode='fly'):
	global dirmode, dirbase
	dirmode = mode if mode else 'fly' # mode == "fly" or "sim"
	dirbase = f'{dirhome}/{dirmode}'

	# factory: 10 DEBUG, 20 INFO, 30 WARNING, 40 ERROR, 50 CRITICAL
	logging.MISSION = 15
	logging.DEBUG = 17

	debug_format = '%(asctime)s %(levelno)s %(module)s %(message)s' 
	debug_fname = f"{makedir()}/debug.log"
	mission_fname = f"{makedir()}/mission.log"

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
	mission_handler = logging.FileHandler(mission_fname, delay=True)
	class MissionFilter(logging.Filter):
		def filter(self, record):
			return record.levelno == logging.MISSION
	mission_handler.addFilter( MissionFilter())
	mission_handler.setLevel(logging.MISSION)
	logger.addHandler(mission_handler)

	logging.info('logging configured')

# is called from both Drone.Cmd and Hippocampus
max_mmo = 179 # maximum mm offset
max_vel = 90 # maximum safe velocity (up to 100)
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
	z = int((z/(max_mmo*2))*(max_vel*2))
	w = int((w/(max_mmo*2))*(max_vel*2))

	s = f'rc {x} {y} {z} {w}'
	return s

def unpack( sdata):
	# data=b'pitch:-2;roll:-2;yaw:2;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:6553;h:0;bat:42;baro:404.45;time:0;agx:-37.00;agy:48.00;agz:-1008.00;'
	adata = sdata.split(';')      # array
	ddata = {}                    # dict
	for stat in adata:
		if len(stat) <= 2: # last item is cr+lf
			break
		name,value = stat.split(':')
		if name in ['ts','tsd','baro','agx','agy','agz']:
			ddata[name] = float(value);
		elif name in ['rc']:
			ddata[name] = str(value);
		else:
			ddata[name] = int(value);
	return ddata 

def soTrue(n, nth): return (n % nth)==0 if nth else False  # nth: 0=none, 1=all, n=every nth

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
