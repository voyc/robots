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

ssid = 'AWACS'
sspw = 'indecent'
ssidsim = 'JASMINE_2G'
sspwsim = '8496HAG#1'
folder = 'home/john/media/webapps/sk8mini/awacs/photos/'
httpstate = 'waiting'  # idle, reading, waiting, dataready
fps = 2
timestamp = time.time()

# globals
camurl = 'http://192.168.4.1'   # when connected to access point AWACS
#camurl = 'http://192.168.1.102'  # when connected as station to JASMINE_2G, cam don't work

imgdir = '/home/john/media/webapps/sk8mini/awacs/photos'
dirname = f'{imgdir}/{time.strftime("%Y%m%d-%H%M%S")}'
ext = 'jpg'

saving = True
showing = False
isverbose = False

# camera settings
framesize = 12	# sxga, 1280 x1024, 5:4, best quality=18
quality = 18
width = 1280
height = 1024

# cropping
cropping = True
w = 600
h = 600
ctrx = 660  # 640
ctry = 466  # 512
x = int(ctrx - (w/2))
y = int(ctry - (h/2))
r = x+w
b = y+h

# execution control
running = True
framenum = 1
firsttime = True

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
	resp = requests.get(url, stream=True).raw	# blocking
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image

def kill():
	running = false

def captureone():
	global framenum
	imagestatus = 'starting'

	if isverbose: 
		print(f'framenum: {framenum}')

	try:
		imagestatus = 'ok'
		image = getImage('capture')
		if len(image) <= 0:
			#print('got image but its empty')
			#continue
			imagestatus = 'empty'
		if verbose: 
			print('got image')
	except:
		imagestatus = 'failed'
	else:
		if cropping:
			image = image[y:b, x:r]
		if showing and firsttime:
			cv2.imshow("windowname", image)
			firsttime = False
		if saving:
			fname = f'{dirname}/{framenum:05}.{ext}'
			if isverbose: 
				print(f'goto save {fname}')
			cv2.imwrite(fname, image)
			if isverbose: 
				print(f'save successful')

	print(f'{framenum} {imagestatus}')
	framenum += 1   # max fps appears to be about 2

	if isverbose: 
		print(f'goto wait')
	time.sleep(.3)  # let settle

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

def getPhoto():
	time.sleep(2)
	logger.info(f'awacs get photo {user}')

	#try:
	#	data = requests.get(url)
	#except Exception as ex:
	#	state = 'error'
	#else:
	#	data = data.strip()
	#	#memcpy data to main process_awacs
	#	#set event
	#	state = 'dataready'
	return '', time.time()


def processPhoto(photo):
	position = [1,2,3]
	return position

def signalMain(position):
	return

def savePhoto(photo, timestamp):
	return

def setupCamera():
	try:
		logging.getLogger("requests").setLevel(logging.WARNING)
		logging.getLogger("urllib3").setLevel(logging.WARNING)

		response = getText(f'control?var=framesize&val={framesize}')
		if response.status_code != 200:
			logger.info(f'awacs set framesize {framesize} : {response.status_code}, {response.text}')
			return False

		response = getText(f'control?var=quality&val={quality}')
		if response.status_code != 200:
			logger.info(f'awacs set quality {quality}: {response.status_code}, {response.text}')
			return False
		logger.info(f'awacs camera setup success')

	except Exception as ex:
		logger.error(f'awacs setupCamera exception {ex}')
		return False

	return True
	

def awacs_loop(n,a):
	global kill_event
	try:
		rc = netup(ssid, sspw)
		if not rc:
			raise
	
		rc = setupCamera()
		if not rc:
			raise
		
		if saving:
			os.mkdir(dirname)

		while True:
			if kill_event.is_set():
				logger.info(f'awacs_loop stopped by kill_event')
				break
			n.value = random.random()
			#photo, timestamp = getPhoto()
			#position = processPhoto(photo)
			#signalMain(position)
			#savePhoto(photo, timestamp)
			time.sleep(.5)
			logger.info(f'awacs loop completed')

	except KeyboardInterrupt:
		logger.error(f'awacs loop keyboard interrupt')
		
	except Exception as ex:
		logger.error(f'awacs loop exception {ex}')

	netdown(ssid)
		

# ---- main process - simulating gcs.py  ----

process_awacs = False
kill_event = False

num = multiprocessing.Value('d', 0.0)
arr = multiprocessing.Array('i', range(10))

def startProcessAwacs():
	global process_awacs, kill_event
	kill_event = multiprocessing.Event()
	process_awacs = multiprocessing.Process(target=awacs_loop, args=(num,arr))
	process_awacs.start()

def stopProcessAwacs():
	global awacstreadstatus, kill_event
	kill_event.set()
	process_awacs.join()

def main():
	logger.setup(True,False)
	net = 'awacs'
	user = 'john'
	pw = 'invincible'
	url = 'localhost:py'
	folder = 'home/john/media/webapps/sk8mini/awacs/photos/'

	startProcessAwacs()
	logger.info('awacs-main process started')

	try:
		while True:
			logger.info('main gcs-skate loop')
			time.sleep( .3)

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
