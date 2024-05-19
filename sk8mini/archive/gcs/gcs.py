'''
gcs.py - ground control station

two modules have sim versions
	awacs - gets frame from camera or disk
	sk8one - pilots the sk8one for real or on the screen based on course

two modules do not have sim version
	vistek - visual cortex, detects object coordinates in the frame
	hippocampus - navigator, plots course based on current coordinates
'''

import subprocess
import logger
import argparse
import sys
import cv2

import vistek
import hippocam

ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/training/'

mode = sys.argv[1]

if mode == 'real':
	import awacs
	import sk8one
elif mode == 'sim':
	import awacsim as awacs
	import sk8onesim as sk8one

ssid = 'AWACS'
sspw = 'indecent'
ssidsim = 'JASMINE_2G'
sspwsim = '8496HAG#1'

def getArgs():
	parser = argparse.ArgumentParser()
	parser.add_argument('mode'                                                     ,help='sim or real'			),
	parser.add_argument('-v'  ,'--verbose'   ,action='store_true' ,default=False   ,help='display additional logging'	),
	parser.add_argument('-q'  ,'--quiet'     ,action='store_true' ,default=False   ,help='suppresses all output'		),
	parser.add_argument('-if' ,'--ifolder'                        ,default=ifolder ,help='input folder'			),
	args = parser.parse_args()	# returns Namespace object, use dot-notation
	return args

def netup(ssid, pw):
	if mode == 'sim':
		return True
	cmd = f'echo "vpn.secrets.password:{pw}" >silly'
	rb = subprocess.check_output(cmd, shell=True)
	cmd = f'nmcli con up {ssid} passwd-file silly'
	rb = subprocess.check_output(cmd, shell=True)
	bo = bytes('success', 'utf-8') in rb
	logger.info(f'{ssid} network connection {"success" if bo else "failure"}')
	return bo

def netdown(ssid):
	if mode == 'sim':
		return True
	cmd = f'nmcli con down {ssid}'
	rb = subprocess.check_output(cmd, shell=True)
	bo = bytes('success', 'utf-8') in rb
	logger.info(f'{ssid} network disconnect {"success" if rc else "failure"}')
	return bo

def sensoryMotorCircuit():
	frame,fnum = awacs.getFrame()
	if len(frame):
		coords = vistek.getCoordinates(frame)
		print(coords)
		course = hippocam.navigate(coords)
		sk8one.pilot(course)
		cones, sk8 = coords
		draw(frame, cones, sk8)
	return frame

def draw(frame, cones,sk8):
	for co in cones:
		cv2.circle(frame, co, 11, (0,0,255), 2)
	co = sk8[0:2]
	cv2.circle(frame, co, 13, (200,0,0), 2)
	cv2.imshow('monitor', frame)
	cv2.waitKey(0)

def main():
	global ssid, sspw
	args = getArgs()
	logger.setup(args.verbose, args.quiet)
	logger.info('starting')
	logger.debug(args)

	rc = netup(ssid, sspw)
	if not rc: return 

	rc = awacs.setup(args.ifolder)
	if not rc: return
	logger.info('awacs online')

	rc = vistek.setup()

	rc = sk8one.setup()
	if not rc: return
	logger.info('sk8one online')

	logger.info('go - press ctrl-c to stop')
	try:
		while True:
			frm = sensoryMotorCircuit()
			if not len(frm):
				logger.info(f'stopped due to no input from awacs')
				break
	except KeyboardInterrupt:
		logger.br(); logger.info(f'operator panic stop')

	rc = netdown(ssid)

if __name__ == '__main__':
	main()
