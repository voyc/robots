''' 
gcs.py  ground control station

runs on laptop

connect to the dongle via serial port

functions:
	receive AHRS data sk8 via serial port dongle running gcs.ino
	connect to awacs webserver and download photo
	detect donut and cone positions from the photo
	detect wheelbase center by combining donut center, helm angle, roll angle
	navigate
	pilot
	send pilot commands to sk8 through the serial port dongle

	gcs
		kill - Ctrl-C
		visualize log - jlog to laptop display
		download photos and labels from awacs and save to disk for ai training
		(opt) visualize arena - matplotlib
		(opt) manual piloting - matplotlib incl keyboard and mouse
	
	awacs
		take photos
		georeference to cover arena
		object detection
	
	sk8
		setup - calibration
		get arena map from awacs
		get position from awacs
		dead reckon position
		command - choose patterns, plan route
		navigate - plot route
		pilot

software architecture
	we decided to use the multiprocessing library to implement 3 processes
	see https://curriculum.voyc.com/doku.php?id=python#software_architecture_options 

throttle adjustment is relative to roll, not helm
	therefore, perhaps we should go back to separate commands
	if doing async, we need events
		onRoll - adjust throttle depending on roll
		onHeading - adjust helm to keep course bearing and/or turn radius
		onPosition - override dead-reckoning position

processes
	gcs - UI
	awacs - camera and CV
	skate - navigation and piloting

shared data
	donut and cones, set by awacs, read by gcs,skate
	center, heading, set by skate, ready by gcs	

	Array('d')
		0 timeDonutUpdated
		1 timeCenterUpdated
	Array('i')
		0 numCones
		1 xDonut
		2 yDonut 
		3 xSkate
		4 ySkate
		5 hSkate
		6 xCone1
		7 yCone1
		8 xCone2
		9 yCone2
		etc.


----------------
sources

object detection:
	folder:  ~/webapps/robots/robots/sk8mini/awacs/detect/
		testconvolve.py  - find donut
		idir = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
		odir = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/'
	scanorm.py - scan a folder of images and a folder of labels, draw the label circle onto the image
	still need the latest find cone algorithm...

navigate:
	~/webapps/robots/robots/autonomy/
		hippoc.py - sim skate path around cones, with video out, using matplotlib and FuncAnimation
		nav.py - library of trigonometry used in navigation

pilot:
	~/webapps/robots/robots/sk8mini/pilot
		pilot.ino - helm and throttle implemented via espwebserver
		pilot.py - manual piloting via keyboard as webserver client, using curses

camera:
	~/webapps/robots/robots/sk8mini/awacs/cam.py

---------------------
todo:

roles:
	captain - design route from choice of patterns 
	navigator - dead reckon position, adjust course
	pilot - keep the vehicle on course
brain parts:
	


add piloting to gcs.py
	for dev and test
		use constants for cones and route
		see hippoc for how this variables are designed

	pull in specs and math
		sk8minimath.py is mostly from arduino/sk8.ino, and currently contains specs, not math 
		see: ~/webapps/robots/robots/autonomy/nav.py - library of trigonometry used in navigation
		write math to adjust throttle depending on roll

	separate throttle and helm commands
		change class PILOT to class CMD
		change PILOT structure in sk8mini.h and skate.py
	
	add onRoll: adjust right-throttle
	
	event-driven
		On roll, adjust throttle
		On heading, dead reckon
		On time elapsed, 
		On position, pilot 
		On cone rounded, navigate
	
	finish figure 8 pattern for calibration, with right throttle adjustment


add navigation
	pull in stuff from hippoc.py

	dead reckoning
		keep list of recent commands
		with each new command, calc new position by adding previous command

feasibiliry of writing images to micro sd card on drone
	size of photos for 10  minut performenace
	size of sd card
	can esp32 connect to a microsd card
	are there arduino demos of writing to an sd card

how to debug multiprocessing
	import pdb; pdb.set_trace()  # not work in child process
'''

import multiprocessing
import time
import argparse
import matplotlib.pyplot as plt

import jlog
from smem import *
import awacs
import skate

# global constants set by cli arguments
verbose	= True
quiet	= False
process	= 'both'

# global variables
args	= False
awacs_process = False
skate_process = False

# shared memory
smem_timestamp = multiprocessing.Array('d', TIME_ARRAY_SIZE) # initialized with zeros
smem_positions = multiprocessing.Array('i', POS_ARRAY_SIZE)  # initialized with zeros


def startAwacs():
	global awacs_process
	awacs_process = multiprocessing.Process(target=awacs.awacs_main, args=(smem_timestamp, smem_positions))
	awacs_process.start()

def startSkate():
	global skate_process
	skate_process = multiprocessing.Process(target=skate.skate_main, args=(smem_timestamp, smem_positions))
	skate_process.start()

def startup():
	if process == 'awacs' or process == 'both':
		startAwacs()
	if process == 'skate' or process == 'both':
		startSkate()

def shutdown():
	global smem_timestamp  # is this necessary
	smem_timestamp[TIME_KILLED] = time.time()
	if awacs_process:
		awacs_process.join()
	if skate_process:
		skate_process.join()

def on_press(event):
	if event.key == 'left':
		jlog.info('UI: turn left')
	if event.key == 'right':
		jlog.info('UI: turn right')
	if event.key == 'up':
		jlog.info('UI: go straight')
	if event.key == 'q':
		jlog.info('UI: kill')
	
def startUI():
	fig, ax = plt.subplots()
	fig.canvas.mpl_connect('key_press_event', on_press)
	ax.set_title('Press a key')
	plt.show()

def main():
	try:
		getCLIargs()
		jlog.setup(verbose, quiet)
		jlog.info('gcs: starting')
		startup()

		startUI()

		# loop
		for i in range(60):
			if smem_timestamp[TIME_KILLED]:
				jlog.info('gcs: stopping due to kill')
				break;
			#drawArena(plan)
			#drawRoute(route)
			time.sleep(1) # nothing else to do until we add visualization
		jlog.debug('gcs: fall out of main loop')

	except KeyboardInterrupt:
		jlog.info('gcs: keyboard interrupt')
		shutdown()

	except Exception as ex:
		jlog.info(f'gcs: main exception: {ex}')
		raise

	try:
		shutdown()
	except Exception as ex:
		jlog.info(f'gcs: shutdown exception: {ex}')

	jlog.info(f'gcs: main exit')
	

class RUNTIME_DEFAULTS:
	# gcs
	process = 'both'

	# skate
	port	= '/dev/ttyUSB0'  # serial port for dongle
	baud	= 115200
	serialtimeout = 3
	serialminbytes = 10
	declination = -1.11 # from magnetic-declination.com depending on lat-lon
	nocal	= False

	# awacs
	sim	= False
	nosave	= False
	noshow	= False
	ssid	= 'AWACS'
	sspw	= 'indecent'
	camurl	= 'http://192.168.4.1'   # when connected to access point AWACS
	framesize= 12	# sxga, 1280 x1024, 5:4, best quality=18
	quality	= 18
	imgdir	= '/home/john/media/webapps/sk8mini/awacs/photos'
	numcones= 9


def getCLIargs(): # get command-line arguments 
	global verbose, quiet, process
	rdef = RUNTIME_DEFAULTS()
	parser = argparse.ArgumentParser()
	parser.add_argument('-v'  ,'--verbose'                    ,action='store_true'        ,help='verbose comments'                 ) 
	parser.add_argument('-q'  ,'--quiet'                      ,action='store_true'        ,help='suppress all output'              )
	parser.add_argument('-ps' ,'--process'                    ,default=rdef.process       ,help='process: both,skate,awacs,none'   )
	parser.add_argument('-p'  ,'--port'                       ,default=rdef.port          ,help='serial port'                      )
	parser.add_argument('-b'  ,'--baud'           ,type=int   ,default=rdef.baud          ,help='serial baud rate'                 )
	parser.add_argument('-st' ,'--serialtimeout'  ,type=int   ,default=rdef.serialtimeout ,help='serial timeout'                   )
	parser.add_argument('-mb' ,'--serialminbytes' ,type=int   ,default=rdef.serialminbytes,help='serial minimum bytes before read' )
	parser.add_argument('-md' ,'--declination'    ,type=float ,default=rdef.declination   ,help='magnetic declination of compass'  )
	parser.add_argument('-nc' ,'--nocal'                      ,action='store_true'        ,help='suppress calibration'             )
	parser.add_argument('-sm' ,'--sim'                        ,action='store_true'        ,help='simulation mode'                  )
	parser.add_argument('-ns' ,'--nosave'                     ,action='store_true'        ,help='suppress save image to disk'      )
	parser.add_argument('-no' ,'--noshow'                     ,action='store_true'        ,help='suppress visualization'           )
	parser.add_argument('-id' ,'--ssid'                       ,default=rdef.ssid          ,help='network ssid'                     )
	parser.add_argument('-pw' ,'--sspw'                       ,default=rdef.sspw          ,help='network password'                 )
	parser.add_argument('-cu' ,'--camurl'                     ,default=rdef.camurl        ,help='URL of camera webserver'          )
	parser.add_argument('-if' ,'--imgdir'                     ,default=rdef.imgdir        ,help='folder for saveing images'        )
	parser.add_argument('-fs' ,'--framesize'      ,type=int   ,default=rdef.framesize     ,help='camera framesize'                 )
	parser.add_argument('-qu' ,'--quality'        ,type=int   ,default=rdef.quality       ,help='camera quality'                   )
	parser.add_argument('-mc' ,'--numcones'       ,type=int   ,default=rdef.numcones      ,help='number of cones in the arena'     )
	args = parser.parse_args()	# returns Namespace object, use dot-notation

	# global
	verbose	= args.verbose
	quiet	= args.quiet

	# gcs
	process	= args.process

	# skate
	skate.verbose	= args.verbose
	skate.quiet	= args.quiet
	skate.port	= args.port
	skate.baud	= args.baud
	skate.serialtimeout = args.serialtimeout
	skate.serialminbytes = args.serialminbytes
	skate.declination = args.declination
	skate.nocal	= args.nocal

	# awacs
	awacs.verbose	= args.verbose
	awacs.quiet	= args.quiet
	awacs.sim	= args.sim
	awacs.nosave	= args.nosave
	awacs.noshow	= args.noshow
	awacs.ssid	= args.ssid
	awacs.sspw	= args.sspw 
	awacs.camurl	= args.camurl
	awacs.framesize	= args.framesize
	awacs.quality	= args.quality
	awacs.imgdir	= args.imgdir
	awacs.numcones	= args.numcones

if __name__ == '__main__':
	main()

