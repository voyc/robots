import cv2
import requests
import numpy as np
import time
import os
import sys

camurl = 'http://192.168.4.1'   # when connected to access point AWACS
#camurl = 'http://192.168.1.102'  # when connected as station to JASMINE_2G, cam don't work
imgdir = '/home/john/sk8mini/awacs/photos'
dirname = f'{imgdir}/{time.strftime("%Y%m%d-%H%M%S")}'
ext = 'jpg'
saving = True
showing = False  #True

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

try:
	framenum = 1
	firsttime = True
	msg = 'starting'
	while True:
		try:
			msg = 'ok'
			image = getImage('capture')
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
				cv2.imwrite(fname, image)
		print(f'{framenum} {msg}')
		framenum += 1   # max fps appears to be about 2
		char = cv2.waitKey(50)
		if char == ord('q'):
			break
		else:
			continue

finally:
	# shut down cleanly
	cv2.destroyAllWindows()

