import cv2
import requests
import numpy as np
import time
import os

camurl = 'http://192.168.4.1'   # when connected to access point AWACS
imgdir = '/home/john/sk8mini/awacs/photos/lenstest'
lensname = 'b_dcxv2'        # 'a_ov2640', 'b_dcxv2', 'c_dcv3r', 'd_longlens'
ext = 'jpg'
saving = True
showing = True

'''
# set framesize and quality
/control?var=quality&val=12

/control?var=framesize&val=13    UXGA  1600 x1200  4:3   best quality=24
/control?var=framesize&val=12    SXGA  1280 x1024  5:4   best quality=14
/control?var=framesize&val=11      HD  1280 x 720 16:9   best quality=10
/control?var=framesize&val=10     XGA  1024 x 768
/control?var=framesize&val= 9    SVGA   800 x 600  4:3   best quality=4(dcxv2=8)
/control?var=framesize&val= 8     VGA   640 x 480
/control?var=framesize&val= 5    QVGA   320 x 240
'''

def takePhoto( framesize, quality, resname):
	getText(f'control?var=framesize&val={framesize}')
	getText(f'control?var=quality&val={quality}')
	time.sleep(.5)

	response = getText('status')
	print(response.status_code)
	print(response.text)

	image = getImage('capture')
	fname = f'{imgdir}/{lensname}_{resname}_{quality}.{ext}'
	print(fname)
	cv2.imwrite(fname, image)

	x = 341
	y = 203
	w = 606
	h = 622
	r = x+w
	b = y+h
	#crop_image = image[x:w, y:h]
	crop_image = image[y:b, x:r]
	fname = f'{imgdir}/{lensname}_{resname}_{quality}_cropped.{ext}'
	cv2.imwrite(fname, crop_image)

def take3():
#	takePhoto( 13, 32, 'uxga');
	takePhoto( 12, 18, 'sxga');
#	takePhoto(  9,  8, 'svga');

def getText(qstring):
	url = f'{camurl}/{qstring}'
	response = requests.get(url)	
	return response

def getImage(qstring):
	url = f'{camurl}/{qstring}'
	resp = requests.get(url, stream=True).raw
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image


take3()

print('done')
