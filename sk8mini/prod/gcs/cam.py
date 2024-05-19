'''
cam.py

cam library 
make a non-blocking http get to awacs/capture with a callback

get an image and save it to disk at 2 fps

usage:

	#include cam

	cam.start(url)

	if cam.dataready
		cam.getdata()

	cam.stop()

threading vs multiprocessing
	with threading: keyboard interrupt stopped main thread but left subthread continuing
	
-----

sources:

original blocking stand-alone http cam program:
	~/webapps/robots/robots/sk8mini/awacs/cam.py

an earlier use of threading:
	~/webapps/robots/robots/sk8/tools/tellomission.py

'''

from multiprocessing import Process, Value, Array
import subprocess
import logger
import time
import random

# ---- awacs_process ----

ssid = 'AWACS'
sspw = 'indecent'
ssid = 'JASMINE_2G'
sspw = '8496HAG#1'
ssidsim = 'JASMINE_2G'
sspwsim = '8496HAG#1'
folder = 'home/john/media/webapps/sk8mini/awacs/photos/'
httpstate = 'waiting'  # idle, reading, waiting, dataready
fps = 2
timestamp = time.time()

def netup(ssid, pw):
	cmd = f'echo "vpn.secrets.password:{pw}" >silly'
	rb = subprocess.check_output(cmd, shell=True)
	cmd = f'nmcli con up {ssid} passwd-file silly'
	rb = subprocess.check_output(cmd, shell=True)
	bo = bytes('success', 'utf-8') in rb
	logger.info(f'{ssid} network connection {"success" if bo else "failure"}')
	return bo

def netdown(ssid):
	cmd = f'nmcli con down {ssid}'
	rb = subprocess.check_output(cmd, shell=True)
	bo = bytes('success', 'utf-8') in rb
	logger.info(f'{ssid} network disconnect {"success" if rb else "failure"}')
	return bo

def getPhoto():
	time.sleep(2)
	print(f'get photo {user}')

	#try:
	#	data = requests.get(url)
	#except Exception as ex:
	#	state = 'error'
	#else:
	#	data = data.strip()
	#	#memcpy data to main processa
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

def loop(n,a):
	logger.setup(True,False)
	netup(ssid, sspw)
	while status != 'stopping':
		try:
			n.value = random.random()
			photo, timestamp = getPhoto()
			position = processPhoto(photo)
			signalMain(position)
			savePhoto(photo, timestamp)
		except:
			print('awacs_process exception')
			break
	netdown(ssid)
		

# ---- main process  ----

processa = False
status = 'init' # init, stopping, running

num = Value('d', 0.0)
arr = Array('i', range(10))

def start():
	global status, processa
	processa = Process(target=loop, args=(num,arr))
	processa.start()
	status = 'running'

def stop():
	global status, thread
	if status == 'running':
		status = 'stopping'
		processa.join()
		
	

'''
import cv2
import requests # blocking
import threading
import numpy as np
import time
import os
import sys

camurl = 'http://192.168.4.1'   # when connected to access point AWACS
#camurl = 'http://192.168.1.102'  # when connected as station to JASMINE_2G, cam don't work
imgdir = '/home/john/media/webapps/sk8mini/awacs/photos'
dirname = f'{imgdir}/{time.strftime("%Y%m%d-%H%M%S")}'
ext = 'jpg'
saving = True
showing = False  #True
isverbose = False #True

framesize = 12
quality = 18

cropping = True
# sxga 1280 x1024  5:4   best quality=18
width = 1280
height = 1024
w = 600
h = 600
ctrx = 660  # 640
ctry = 466  # 512
x = int(ctrx - (w/2))
y = int(ctry - (h/2))
r = x+w
b = y+h

print(x)
print(y)

if len(sys.argv) > 1:
	if sys.argv[1] == 'nocrop':
		print('no cropping')
		cropping = False;

def getText(qstring):
	url = f'{camurl}/{qstring}'
	response = requests.get(url, timeout=3)	
	return response

def getImage(qstring):
	url = f'{camurl}/{qstring}'
	resp = requests.get(url, stream=True).raw
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image

try:
	getText(f'control?var=framesize&val={framesize}')
	getText(f'control?var=quality&val={quality}')
except:
	print('http get failed')
	quit()

time.sleep(.5)

response = getText('status')
print(response.status_code)
print(response.text)

if saving:
	os.mkdir(dirname)

framenum = 1
firsttime = True
msg = 'starting'
if isverbose:
	print('starting')

while True:
	if isverbose: 
		print(f'framenum: {framenum}')
	try:
		msg = 'ok'
		image = getImage('capture')
		if len(image) <= 0:
			print('got image but its empty')
			continue
		if isverbose: 
			print('got image')
	except KeyboardInterrupt:
		print('keyboard interrupt')	
		quit()
	except:
		msg = 'failed'
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
	print(f'{framenum} {msg}')
	framenum += 1   # max fps appears to be about 2
	if isverbose: 
		print(f'goto wait')

	time.sleep(.3)  # let settle
'''
