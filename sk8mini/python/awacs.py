'''
awacs.py - awacs library imported by gcs.py

runs in the awacs_process, launched by gcs.py 
communicates with awacs.ino via webserver

functions:
	switch laptop to awacs wifi network
	make an http request to get a photo
	detect objects in the photo
	share object positions with other processes

---------------
sources:

camera:  original blocking stand-alone http cam program:
	~/webapps/robots/robots/sk8mini/awacs/cam.py

an earlier use of threading:
	~/webapps/robots/robots/sk8/tools/tellomission.py

detect donut
	~/webapps/robots/robots/sk8mini/archive/awacs/detect/testdonut.py
	~/webapps/robots/robots/sk8mini/detect/testdonut.py
	~/webapps/robots/robots/sk8mini/detect/scanorm.py

detect cones
	still need the latest find cone algorithm...

---------------------
issues:

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

feasibiliry of writing images to micro sd card on drone
	size of photos for 10  minut performenace
	size of sd card
	can esp32 connect to a microsd card
	are there arduino demos of writing to an sd card
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
import argparse

import jlog
from smem import *

def setupArgParser(parser):
	# runtime directives
	parser.add_argument('--nosave'  ,action='store_true'           ,help='suppress save image to disk')

	# webserver settings
	parser.add_argument('--ssid'    ,default='AWACS'               ,help='network ssid, alternate JASMINE_2')
	parser.add_argument('--sspw'    ,default='indecent'            ,help='network password, alternate 8496HAG#1')
	parser.add_argument('--camurl'  ,default='http://192.168.4.1'  ,help='URL of camera webserver, alt http://192.168.1.102')

	# disk filenames
	parser.add_argument('--imgdir'  ,default='/home/john/media/webapps/sk8mini/awacs/photos' ,help='folder for saving images')
	parser.add_argument('--kernel'  ,default='/home/john/media/webapps/sk8mini/awacs/photos/crop/donutfilter.jpg' ,help='fname of donutkernel')

	# camera settings
	parser.add_argument('--framesize' ,default=12   ,type=int        ,help='camera framesize')
	parser.add_argument('--quality'   ,default=18   ,type=int        ,help='camera quality')

	# object detection
	parser.add_argument('--numcones'  ,default=9    ,type=int        ,help='number of cones in the arena')

# the following globals are set during startup BEFORE the process starts
args = None   # command-line arguments

# camera settings
cameraSettleTime = .3

# disk filenames
imgext = 'jpg'

# image dimensions
width = 1280 # determined by camera framesize setting
height = 1024
w = 600   # arbitrary arena size
h = 600

# cropping boundaries
ctrx = 660  # 640
ctry = 466  # 512
x = int(ctrx - (w/2))
y = int(ctry - (h/2))
r = x+w
b = y+h

# the following globals are used only within awacs_process
photo_timestamp = 0.0
donutkernel = None
dirname = ''


def setCenter(x,y):
	global ctrx, ctry
	ctrx = x
	ctry = y

def getText(qstring):
	url = f'{args.camurl}/{qstring}'
	response = requests.get(url, timeout=10)	# blocking
	return response

def getImage(qstring):
	url = f'{args.camurl}/{qstring}'
	timestampReq = time.time()
	resp = requests.get(url, stream=True, timeout=10).raw	# blocking
	timestampResp = time.time()
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image, timestampReq, timestampResp

def capturePhoto():
	try:
		image,start,stop = getImage('capture')
		if len(image) <= 0:
			raise Exception('{start} image returned empty')
	except Exception as ex:
		jlog.error(f'capture photo {start} error {ex}')
		raise

	jlog.debug(f'awacs: photo captured {start}')
	return image, start, stop  # do we shut down on one excepton or keep going to retry?

def cropPhoto(image):
	image = image[y:b, x:r]
	return image

def geoReference(photo):
	return cv2.rotate(photo, cv2.ROTATE_180)

def savePhoto(image, timestamp):
	if not args.nosave:
		fname = f'{dirname}/{timestamp}.{imgext}'
		cv2.imwrite(fname, image)
		jlog.debug(f'awacs: saved {fname}')

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

def setupCamera():
	try:
		jlog.debug('getText framesize')
		response = getText(f'control?var=framesize&val={args.framesize}')
		if response.status_code != 200:
			raise Exception(f'awacs: camera framesize response {response.status_code}')
		jlog.debug('got framesize')

		jlog.debug('getText quality')
		response = getText(f'control?var=quality&val={args.quality}')
		if response.status_code != 200:
			raise Exception(f'awacs: camera quality response {response.status_code}')
		jlog.debug('got quality')

		time.sleep(.5)
		response = getText('status')
		jlog.debug(response.status_code)
		jlog.debug(response.text)
	except Exception as ex:
		raise Exception(f'awacs: setupCamera exception: {ex}')
	jlog.info(f'awacs: camera setup comlete')
	
def prepDonutKernel(fname):
	kernel = cv2.imread(fname)
	kernel = cv2.cvtColor(kernel, cv2.COLOR_BGR2GRAY)
	kernel = ((kernel / 255) - 0.5) * 2 # normalize to -1:+1
	return kernel

def findDonut(frame, kernel):
	frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	frame = ((frame / 255) - 0.5) * 2 # normalize to -1:+1
	convolved = cv2.filter2D(frame, 1, kernel)
	cidx = np.argmax(convolved)
	cx = cidx % 600
	cy = int(cidx / 600)
	return cx, cy

def findCones(photo, numCones):
	cones = [[0,0]] * numCones # an array of x,y points
	for i in range(0,numCones):
		cones[i][0] = random.randint(0,600)
		cones[i][1] = random.randint(0,600)
	return cones

def processAerialPhoto():
	global photo_timestamp

	# captures fail if too close together.  Is it http or camera?
	sleeptime = cameraSettleTime - (time.time() - photo_timestamp)
	if sleeptime > 0:
		time.sleep(sleeptime)

	# get photo from camera
	photo, start, stop = capturePhoto()
	photo_timestamp = start # closest time as possible to actual camera capture
	jlog.debug(f'awacs: got photo, elapsed {stop - start}')

	# prep photo
	photo = cropPhoto(photo)
	photo = geoReference(photo)

	# object recognition
	x,y = findDonut(photo, donutkernel)
	acones = findCones(photo, args.numcones)
	jlog.debug(f'awacs: got objects, donut at {x},{y}')

	# move object positions to shared memory
	gmem_positions[NUM_CONES] = len(acones)
	gmem_positions[DONUT_X] = x
	gmem_positions[DONUT_Y] = y
	pos = CONE1_X
	for i in range(len(acones)): 
		gmem_positions[pos + i*2] = acones[i][0]
		gmem_positions[pos + i*2 + 1] = acones[i][1]
	gmem_timestamp[TIME_PHOTO] = photo_timestamp
	
	# save to disk for ex post facto analysis
	savePhoto(photo, photo_timestamp)

def awacs_main(timestamp, positions):
	global args, gmem_timestamp, gmem_positions, donutkernel, dirname
	gmem_timestamp = timestamp
	gmem_positions = positions	

	try: 
		jlog.setup(args.verbose, args.quiet)

		# ignore the KeyboardInterrupt in this subprocess
		signal.signal(signal.SIGINT, signal.SIG_IGN)

		# setup
		jlog.debug(f'awacs: starting process id: {os.getpid()}')
		netup(args.ssid, args.sspw)
		setupCamera()
		donutkernel = prepDonutKernel(args.kernel)
		if not args.nosave:
			dirname = f'{args.imgdir}/{time.strftime("%Y%m%d-%H%M%S")}'
			os.mkdir(dirname)

		# get first framed
		processAerialPhoto()

		# wait here until everybody ready
		jlog.info('awacs: ready')
		timestamp[TIME_AWACS_READY] = time.time()
		while not timestamp[TIME_READY] and not timestamp[TIME_KILLED]:
			time.sleep(.1)

		# main loop
		while True:
			if timestamp[TIME_KILLED]:
				jlog.info(f'awacs: stopping due to kill')
				break
			processAerialPhoto()

		jlog.debug('awacs: fall out of main loop')

	except KeyboardInterrupt:
		jlog.error('never happen')
		
	except Exception as ex:
		jlog.error(f'awacs: exception: {ex}')
		timestamp[TIME_KILLED] = time.time()

	try:
		netdown(ssid)
	except:
		pass
	jlog.info(f'awacs: main exit')

