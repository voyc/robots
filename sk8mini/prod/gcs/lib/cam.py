'''
lib/cam.py

a library of camera functions used by gcs.py

functions:
	connect to the awacs network
	make an http get to capture an image
	crop the image
	save the image to disk
	make the image available for object detection

async http requests:
	the python requests library handles http requests, but it is blocking
	therefore, each request must be done in a thread,
	or, the whole loop could be done in a thread

	from the requests documentation, 
	projects that combine Requests with one of Python’s asynchronicity frameworks:
		requests-threads
		grequests
		requests-futures	
		httpx

event driven programming options:
	asyncio - manual context-switch, lower overhead than multi-threading (use for IO-bound apps?), coroutines
	multi-threading/processing - OS determined context-switch (use for CPU-bound apps?), events and queues
	other:
		turtle - doc examples cover only mouse, keyboard, and timer
		pyeventus - uses asyncio
		
gcs threads, coroutines:
	espnow - continuously receiving data from dongle via Serial port, input to piloting, position correction
	http - continuously requestino and waiting for image from http get request
	object detection - between http and position correction, execute when http request received
	navigation - long-term strategic decisions, input to piloting 
	piloting - PID, bearing correction
	dead reckoning - calculating current position, needed for piloting 
	position correction - override and reset dead reckoning, needed for piloting
	ui-display - matplotlib animation
	ui-input - mouse and keyboard events (matplotlib)

speed:
	we are getting 2 fps, before multithreading, and including saving
	todo: profile the get and the save

--------------

speed up position acquisition:

	image data transfer: 
		http - built into laptop wifi, python multi-tasking required 
		espnow - esp32 dongle required
		radio - how to get high-speed radio data into computer without serial dongle?
	
	transfer from dongle to computer
		what is serial speed?

	save images for ai training
		separate program.  2fps for saving, 5fps for realtime ops
		multi-tasking

	onboard object recognition
		Look at aithinker examples on GitHub.
			Isolate camera code from webserver code 
			Find face recog code.
			Get other types beside jpeg from the camera.
			What are the types?  Get bitmap.
			time required for compression, decompression?

		functions:
			Choose rect near the previous position.
			Crop
			grayscale, simultaneously with crop
			Convolute

'''

import cv2
import requests
import numpy as np
import time
import os
import sys


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
	response = requests.get(url, timeout=3)				# block
	return response

def getImage(qstring):
	url = f'{camurl}/{qstring}'
	resp = requests.get(url, stream=True).raw			# block
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image

def start():
	print(x)
	print(y)
	
	if len(sys.argv) > 1:
		if sys.argv[1] == 'nocrop':
			print('no cropping')
			cropping = False;
	
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
	if isverbose:
		print('starting')

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

def capture():
	while running:
		captureone()

def main():
	capture()

if __name__ == '__main__':
	main()

