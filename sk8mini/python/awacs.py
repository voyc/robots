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

usage:
	import awacs

	awacs.start(url)

	if awacs.dataready
		awacs.getdata()

	awacs.stop()

-----

software architecture options

synchronous
	a set of tasks must be executed one-at-a-time in a specific order	

async 
	a set of tasks can be run in any order, and maybe simultaneously 
	each task may be interruptible

blocking
	with a synchronous design, long-running tasks run until completion, blocking any other tasks 

	python's native http libraries all block between request and response
		over 1700 python libraries for http, and every one of them blocks:
			requests.get( url) blocks
			http.client.getResponse() blocks
			urllib3.PoolManager().request() blocks
			etc
	this is the opposite of http's design intention: an unthinkable	implementation

	the requests library has the tagline: "http for humans"
		this implies:
			the library authors find http progamming difficult
			so they are here to save the day by simplifying it
		in fact:
			a better tagline would be: "http for amateurs"

event-driven
	event-driven design is one example of async design
	using callbacks or signals
	make an http request and return immediately
	on receipt of the response, set a signal or call a callback

cooperative multitasking
	asyncio is an example of cooperative multitasking
	the programmer inserts an await directive into a function
		where it is appropriate to interrupt the function and allow other tasks to run

preemptive multitasking
	the os decides when to interrupt a task

asyncio
	a python library
	implements cooperative multitasking
	def async functionname(): - defines an interruptible function
	await - a directive placed within an async function to yield cpu to other async functions
	all threads run in one process, which means 
		they can theoretically run async (non-blocking), but not simultaneously
	the python http libraries do not allow a place to put the await directive
		between the request and the response, 
		so the asyncio library does not solve the http blocking problem
	because we call requests.get() within a subprocess
		the combinatino of asyncio and subprocess might work

threading
	a python library
	programmer can start multiple threads and assign functions to each thread
	all threads run in one process
	the global interpreter lock (GIL) - in CPython, a predominate python interpreter - 
		prevents two threads from executing python code simultaneously,
	therefore, threads can execute async (non-blocking), but not simultaneously

multiprocessing
	a python library
	similar to threading, but using "process" instead of "thread"
	each process can be assigned to a different cpu or core, 
		allowing multiple tasks to run simultaneously

-----

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

import multiprocessing
import subprocess
import logging
import logger
import time
import random
import cv2
import requests
import numpy as np
import time
import os
import sys

# ---- awacs_process ----

### global constants, can be set by main process before awacs_process begins

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
cropping = True
saving = True
showing = False
isverbose = False

# camera settings
framesize = 12	# sxga, 1280 x1024, 5:4, best quality=18
quality = 18
width = 1280
height = 1024
w = 600
h = 600

# object detection
maxCones = 9
### global variables, used only within execution control

framenum = 1
firsttime = True
fps = 2

# cropping boundaries, calculated one time after first photo
ctrx = 660  # 640
ctry = 466  # 512
x = int(ctrx - (w/2))
y = int(ctry - (h/2))
r = x+w
b = y+h

def setCenter(x,y):
	global ctrx, ctry
	ctrx = x
	ctry = y

def getText(qstring):
	url = f'{camurl}/{qstring}'
	response = requests.get(url, timeout=3)	# blocking
	return response

def getImage(qstring):
	url = f'{camurl}/{qstring}'
	timestampReq = time.time()
	resp = requests.get(url, stream=True).raw	# blocking
	timestampResp = time.time()
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image, timestampReq, timestampResp

def capturePhoto():
	global framenum
	logger.debug(f'capture photo framenum: {framenum}')

	try:
		image,start,stop = getImage('capture')
		if len(image) <= 0:
			raise Exception('frame {framenum} image returned empty')
	except Exception as ex:
		logger.error(f'frame {framenum} error {ex}')
		raise

	logger.debug(f'frame {framenum} success')
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
		if isverbose: 
			print(f'goto save {fname}')
		cv2.imwrite(fname, image)
		if isverbose: 
			print(f'save successful')

def netup(ssid, pw):
	cmd = f'echo "vpn.secrets.password:{pw}" >silly'
	rb = subprocess.check_output(cmd, shell=True)
	cmd = f'nmcli con up {ssid} passwd-file silly'
	rb = subprocess.check_output(cmd, shell=True)
	bo = bytes('success', 'utf-8') in rb
	logger.info(f'awacs {ssid} network connection {"success" if bo else "failure"}')
	return bo

def netdown(ssid):
	cmd = f'nmcli con down {ssid}'
	rb = subprocess.check_output(cmd, shell=True)
	bo = bytes('success', 'utf-8') in rb
	logger.info(f'awacs {ssid} network disconnect {"success" if rb else "failure"}')
	return bo


def processPhoto(photo):
	position = [1,2,3]
	return position

def signalMain(position):
	return

def savePhoto(photo, timestamp):
	return

def setupCamera():
	try:
		logging.getLogger("requests").setLevel(logging.WARNING) # quiet
		logging.getLogger("urllib3").setLevel(logging.WARNING) # quiet

		response = getText(f'control?var=framesize&val={framesize}')
		if response.status_code != 200:
			logger.error(f'awacs set framesize {framesize} : {response.status_code}, {response.text}')
			return False

		response = getText(f'control?var=quality&val={quality}')
		if response.status_code != 200:
			logger.error(f'awacs set quality {quality}: {response.status_code}, {response.text}')
			return False
	except Exception as ex:
		logger.error(f'awacs setupCamera exception {ex}')
		return False

	logger.info(f'awacs camera setup success')
	return True
	
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

def awacs_loop(timestamp, positions):
	global kill_awacs_event
	logger.setup(True,False)
	try: 
		# setup
		logger.debug(f'awacs process id: {os.getpid()}')

		rc = netup(ssid, sspw)
		if not rc:
			raise Exception('netup returned false')
	
		rc = setupCamera()
		if not rc:
			raise Exception('setupCamera returned false')
		
		if saving:
			os.mkdir(dirname)

		# get first frame, find center donut, calcCropBoundaries
		# useful if the quadstring camera position is altered

		logger.info('awacs process setup complete, begin loop')

		while True:
			if kill_awacs_event.is_set():
				logger.info(f'awacs_loop stopped by kill_awacs_event')
				break

			photo, start, stop = capturePhoto()
			photo = cropPhoto(photo)
			x,y = findDonut(photo)
			acones = findCones(photo, maxCones)

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
			logger.debug(f'awacs loop iteration completed')

	except KeyboardInterrupt:
		logger.error(f'awacs loop keyboard interrupt')
		
	except Exception as ex:
		logger.error(f'awacs loop exception: {ex}')

	netdown(ssid)
		

# ---- main process - simulating gcs.py  ----

# global variabless used in main process
process_awacs = False
kill_awacs_event = False

# shared memory
smem_timestamp = multiprocessing.Value('d', 0.0)
smem_positions = multiprocessing.Array('i', range((maxCones+1)*2+1)) # [3, dx,dy, x1,y1, x2,y2, x3,y3]

def startProcessAwacs():
	global process_awacs, kill_awacs_event
	kill_awacs_event = multiprocessing.Event()
	process_awacs = multiprocessing.Process(target=awacs_loop, args=(smem_timestamp, smem_positions))
	process_awacs.start()

def stopProcessAwacs():
	global awacstreadstatus, kill_awacs_event
	kill_awacs_event.set()
	process_awacs.join()

def aerialPosition(timestamp, donut, cones):
	numCones = len(cones)
	logger.info(f'photo time: {timestamp}, donut: {donut}, {numCones} cones: {cones}')

def main():
	logger.setup(True,False)

	# command-line arguments
	imgdir = 'home/john/media/webapps/sk8mini/awacs/photos/'
	maxCones = 9

	# start child process
	startProcessAwacs()
	logger.info('awacs-main process started')
	aerial_timestamp = 0.0

	logger.info('main setup complete, begin main loop')
	
	try:
		logger.info(f'main process id:, {os.getpid()}')
		while True:
			# get donut, cones, and timestamp from shared memory
			if smem_timestamp.value > aerial_timestamp:
				logger.debug(f'main retrieve shared memory')
				aerial_timestamp = smem_timestamp.value
				numCones = smem_positions[0]
				donut = [0,0]
				cones = [[0,0]] * numCones
				donut[0] = smem_positions[1]
				donut[1] = smem_positions[2]
				pos = 3
				for i in range(numCones): 
					cones[i][0] = smem_positions[pos + i*2]
					cones[i][1] = smem_positions[pos + i*2 + 1]
				aerialPosition( aerial_timestamp, donut, cones)
				logger.debug('return from aerialPosition')

			time.sleep( .3)
			logger.debug(f'main loop iteration completed')

	except KeyboardInterrupt:
		logger.info('main keyboard interrupt')

	except Exception as ex:
		logger.info(f'main exception {ex}')
	finally:
		stopProcessAwacs()
		logger.info(f'main process_awacs stopped')

	logger.info('main exit')

if __name__ == '__main__':
	main()
