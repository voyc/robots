'''
awacs.py - awacs module

this will ultimately reside on the awacs vehicle

get an aerial photo from the camera
preprocess the photo
detect the cones
detect the sk8
make the sk8 and cones available to the gcs

'''

import requests
import logger

# global constants
awacsurl = 'http://192.168.4.1'   # when connected to access point AWACS

def getText(qstring):
	url = f'{awacsurl}/{qstring}'
	response = requests.get(url, timeout=3)	
	return response

def getImage(qstring):
	url = f'{awacsurl}/{qstring}'
	resp = requests.get(url, stream=True).raw
	image = np.asarray(bytearray(resp.read()), dtype="uint8")
	image = cv2.imdecode(image, cv2.IMREAD_COLOR)
	return image

def setup():
	bo = True
	try:
		getText(f'control?var=framesize&val={framesize}')
		getText(f'control?var=quality&val={quality}')

		time.sleep(.5)

		response = getText('status')
		print(response.status_code)
		print(response.text)

		if response != 200:
			bo = False
	except:
		print('http get failed')
		bo = False

	return bo

def getCoordinates():
	frame = getFrame()
	logger.info('got frame')

def getFrame():
	pass


