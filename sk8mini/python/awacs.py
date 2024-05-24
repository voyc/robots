'''
awacs.py - awacs library imported by gcs.py

maintain two processes: main and awacs
in the main process:
	start
	stop
in the awacs process loop:
	make a non-blocking http get to awacs/capture and receive an image in the response
	get the image and save it to disk at 2 fps
	process the image

------

speed of image transfer from microcontroller to laptop python

1A. espnow speed from microcontroller to dongle
	using 256-byte blocks

1B. serial speed from dongle to laptop
	serial port baud (bps)
	 230400   230.4k
	 250000   250.0k
	 500000   500.0k  0.5M
	1000000  1000.0k  1M
	2000000  2000.0k  2M
	https://docs.google.com/spreadsheets/d/1Q4BNd_W7z0au821rS-OkA7xuXR-tvCHPNgH-RJ5blN4/edit?usp=sharing

2. http speed
	high latency, with random delays

-----

sources:

original blocking stand-alone http cam program:
	~/webapps/robots/robots/sk8mini/awacs/cam.py

an earlier use of threading:
	~/webapps/robots/robots/sk8/tools/tellomission.py

'''

import signal
import time
import random
import cv2
import requests
import numpy as np
import os
import sys
import nmcli

import jlog
from smem import *

# ---- awacs_process ----

### global constants, set by gcs.py main process before awacs_process begins

# webserver settings
ssid = 'AWACS'
sspw = 'indecent'
camurl = 'http://192.168.4.1'   # when connected to access point AWACS

ssidsim = 'JASMINE_2G'
sspwsim = '8496HAG#1'
camurlsim = 'http://192.168.1.102'  # when connected as station to JASMINE_2G, cam don't work

# disk filenames
imgdir = '/home/john/media/webapps/sk8mini/awacs/photos'
dirname = f'{imgdir}/{time.strftime("%Y%m%d-%H%M%S")}'
ext = 'jpg'

# runtime options
sim = True
crop = True
save = True
show = False
verbose = True
quiet = False

# camera settings
framesize = 12	# sxga, 1280 x1024, 5:4, best quality=18
quality = 18

# object detection
numcones = 9

### global semi-constants, set one-time within the awacs_process

# image dimensions
width = 1280 # determined by camera framesize setting
height = 1024
w = 600   # arbitrary arena size
h = 600

# cropping boundaries, calculated one time after first photo
ctrx = 660  # 640
ctry = 466  # 512
x = int(ctrx - (w/2))
y = int(ctry - (h/2))
r = x+w
b = y+h

### global variables, used only within the awacs_process process
framenum = 1  # used in capturePhoto and savePhoto
firsttime = True   # used only in showPhoto
fps = 2  # not used

def setCenter(x,y):
	global ctrx, ctry
	ctrx = x
	ctry = y

def getText(qstring):
	url = f'{camurl}/{qstring}'
	response = requests.get(url, timeout=10)	# blocking
	return response

def getImage(qstring):
	url = f'{camurl}/{qstring}'
	timestampReq = time.time()
	resp = requests.get(url, stream=True, timeout=10).raw	# blocking
	timestampResp = time.time()
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image, timestampReq, timestampResp

def capturePhoto():
	global framenum
	jlog.debug(f'capture photo framenum: {framenum}')

	try:
		image,start,stop = getImage('capture')
		if len(image) <= 0:
			raise Exception('frame {framenum} image returned empty')
	except Exception as ex:
		jlog.error(f'frame {framenum} error {ex}')
		raise

	jlog.debug(f'frame {framenum} success')
	framenum += 1
	return image, start, stop  # do we shut down on one excepton or keep going to retry?

def cropPhoto(image):
	if cropping:
		image = image[y:b, x:r]
	return image

def showPhoto():
	if showing and firsttime:
		cv2.imshow("windowname", image)
		firsttime = False

def savePhoto():
	if saving:
		fname = f'{dirname}/{framenum:05}.{ext}'
		jlog.info(f'goto save {fname}')
		cv2.imwrite(fname, image)
		jlog.info(f'save successful')

def netup(ssid, pw):
	try:
		nmcli.disable_use_sudo()
		nmcli.device.wifi_rescan()
		nmcli.device.wifi_connect(ssid, pw)
	except Exception as ex:
		jlog.error(f'awacs: connect to {ssid} failed: {ex}')
		raise Exception('connection failed')
	jlog.info(f'awacs: connected to {ssid}')

def isNetUp( ssid):
	a = nmcli.device.wifi()
	for dev in a:
		if dev.in_use and dev.ssid == ssid:
			return True
	return False

def netdown(ssid):
	try:
		if isNetUp(ssid):
			nmcli.connection.down(ssid)
	except Exception as ex:
		jlog.error(f'awacs: {ssid} disconnect failed: {ex}')
		raise Exception('disconnect failed')

def processPhoto(photo):
	position = [1,2,3]
	return position

def signalMain(position):
	return

def savePhoto(photo, timestamp):
	return

def setupCamera():
	try:
		jlog.debug('getText framesize')
		response = getText(f'control?var=framesize&val={framesize}')
		jlog.debug('got framesize')
		if response.status_code != 200:
			raise Exception(f'awacs: camera framesize response {response.status_code}')
		jlog.debug('getText quality')
		jlog.debug('got quality')
		response = getText(f'control?var=quality&val={quality}')
		if response.status_code != 200:
			raise Exception(f'awacs: camera quality response {response.status_code}')

		time.sleep(.5)
		response = getText('status')
		jlog.debug(response.status_code)
		jlog.debug(response.text)
	except Exception as ex:
		raise Exception(f'awacs: setupCamera exception: {ex}')
	jlog.info(f'awacs: camera setup comlete')
	
def findDonut(photo):
	x = -1
	y = -1
	return x,y

def findCones(photo, numCones):
	cones = [[0,0]] * numCones # an array of x,y points
	for i in range(0,numCones):
		cones[i][0] = random.randint(0,600)
		cones[i][1] = random.randint(0,600)
	return cones

def awacs_main(timestamp, positions):
	try: 
		jlog.setup(verbose, quiet)

		# ignore the KeyboardInterrupt in this subprocess
		signal.signal(signal.SIGINT, signal.SIG_IGN)

		# setup
		jlog.debug(f'awacs: starting process id: {os.getpid()}')
		netup(ssid, sspw)
		setupCamera()
		if saving:
			os.mkdir(dirname)

		# get first frame, find center donut, calcCropBoundaries
		# useful if the quadstring camera position is altered

		jlog.info('awacs: setup complete, begin loop')

		while True:
			if timestamp[TIME_KILLED]:
				jlog.info(f'awacs: stopping due to kill')
				break

			photo, start, stop = capturePhoto()
			photo = cropPhoto(photo)
			x,y = findDonut(photo)
			acones = findCones(photo, numcones)

			# move donut, cones and timestamp to shared memory
			positions[0] = len(acones)
			positions[1] = x
			positions[2] = y
			pos = 3
			for i in range(len(acones)): 
				positions[pos + i*2] = acones[i][0]
				positions[pos + i*2 + 1] = acones[i][1]
			timestamp.value = start
			
			#savePhoto(photo, timestamp)

			time.sleep(.3)  # if too close, http request fails
			jlog.debug(f'awacs: loop iteration completed')

	except KeyboardInterrupt:
		jlog.error('never nappen')
		
	except Exception as ex:
		jlog.error(f'awacs: exception: {ex}')
		timestamp[TIME_KILLED] = time.time()

	try:
		netdown(ssid)
	except:
		pass
	jlog.info(f'awacs: main exit')
		

# ---- main process - simulating gcs.py  ----

## global variabless used in main process
#process_awacs = False
#kill_awacs_event = False
#
## shared memory
#smem_timestamp = multiprocessing.Value('d', 0.0)
#smem_positions = multiprocessing.Array('i', range((maxCones+1)*2+1)) # [3, dx,dy, x1,y1, x2,y2, x3,y3]
#
#def startProcessAwacs():
#	global process_awacs, kill_awacs_event
#	kill_awacs_event = multiprocessing.Event()
#	process_awacs = multiprocessing.Process(target=awacs_main, args=(smem_timestamp, smem_positions))
#	process_awacs.start()
#
#def stopProcessAwacs():
#	global awacstreadstatus, kill_awacs_event
#	kill_awacs_event.set()
#	process_awacs.join()
#
#def aerialPosition(timestamp, donut, cones):
#	numCones = len(cones)
#	jlog.info(f'photo time: {timestamp}, donut: {donut}, {numCones} cones: {cones}')
#
#def main():
#	global sim, ssid, sspw
#	jlog.setup(True,False)
#
#	# command-line arguments
#	imgdir = 'home/john/media/webapps/sk8mini/awacs/photos/'
#	maxCones = 9
#	sim = True
#	if sim:
#		ssid = ssidsim
#		sspw = sspwsim
#
#	# start child process
#	startProcessAwacs()
#	jlog.debug('awacs-main process started')
#	aerial_timestamp = 0.0
#
#	jlog.info('main setup complete, begin main loop')
#	
#	try:
#		jlog.info(f'main process id:, {os.getpid()}')
#		while True:
#			# get donut, cones, and timestamp from shared memory
#			if smem_timestamp.value > aerial_timestamp:
#				jlog.debug(f'main retrieve shared memory')
#				aerial_timestamp = smem_timestamp.value
#				numCones = smem_positions[0]
#				donut = [0,0]
#				cones = [[0,0]] * numCones
#				donut[0] = smem_positions[1]
#				donut[1] = smem_positions[2]
#				pos = 3
#				for i in range(numCones): 
#					cones[i][0] = smem_positions[pos + i*2]
#					cones[i][1] = smem_positions[pos + i*2 + 1]
#				aerialPosition( aerial_timestamp, donut, cones)
#				jlog.debug('return from aerialPosition')
#
#			time.sleep( .3)
#			jlog.debug(f'main loop iteration completed')
#
#	except KeyboardInterrupt:
#		jlog.info('main keyboard interrupt')
#
#	except Exception as ex:
#		jlog.info(f'main exception {ex}')
#	finally:
#		stopProcessAwacs()
#		jlog.info(f'main process_awacs stopped')
#
#	jlog.info('main exit')
#
#if __name__ == '__main__':
#	main()
