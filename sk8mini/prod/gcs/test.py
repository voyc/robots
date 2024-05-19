'''
test.py
a vesion of gcs.py to test camthread.py
'''

import time
import cam
import logger


cam.net = 'awacs'
cam.user = 'john'
cam.pw = 'invincible'
cam.url = 'localhost:py'
cam.folder = 'home/john/media/webapps/sk8mini/awacs/photos/'



def loop():
	while True:
		print(f'gcs {cam.num.value}')
		time.sleep(.3)

	cam.stop()

def main():
	logger.setup(True, False)
	cam.start()

	try:
		loop()
	except:
		print('main process exception')

	cam.stop()

main()

