import cv2
import requests
import numpy as np
import time
import os

camurl = 'http://192.168.4.1'
imgdir = '/home/john/sk8mini/awacs/photos'
dirname = f'{imgdir}/{time.strftime("%Y%m%d-%H%M%S")}'
ext = 'jpg'
saving = True
showing = True

# set resolution: vga 640x480



# set quality: 32









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

response = getText('status')
print(response.status_code)
print(response.text)

if saving:
	os.mkdir(dirname)

try:
	framenum = 1
	while True:
		image = getImage('capture')
		if showing:
			cv2.imshow("windowname", image)
		if saving:
			fname = f'{dirname}/{framenum:05}.{ext}'
			cv2.imwrite(fname, image)
		print(framenum)
		framenum += 1   # max fps appears to be about 2
		char = cv2.waitKey(50)
		if char == ord('q'):
			break
		else:
			continue

finally:
	# shut down cleanly
	cv2.destroyAllWindows()

