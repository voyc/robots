''' 
gcs.py  ground control station

runs on laptop
connects to serial port dongle

functions:
	this is the main executable
	get runtime options from the command line
	manage UI
	start two child processes: awacs and skate 

software architecture:
	we decided to use the multiprocessing library to implement 3 processes
	see https://curriculum.voyc.com/doku.php?id=python#software_architecture_options 

	3 components:
		gcs - UI
			kill - Ctrl-C
			visualize log - jlog to laptop display
			download photos and labels from awacs and save to disk for ai training
			(opt) visualize arena - matplotlib
			(opt) manual piloting - matplotlib incl keyboard and mouse
		
		awacs - camera and CV
			take photos
			georeference to cover arena
			object detection
		
		skate - navigation and piloting
			setup - calibration
			get arena map from awacs
			get position from awacs
			dead reckon position
			command - choose patterns, plan route
			navigate - plot route
			pilot
	
	shared data: mapped in smem.py 

----------------
issues:
	how to debug multiprocessing:
		import pdb; pdb.set_trace()  # does not work in child process

	python exceptions:
		the purpose of catching an exception, is to prevent the program from interrupting
		so if you want the program to interrupt, you must take action
			1. raise - run the finally clause and then goto outer try
			2. return - rund the finally clause and then return from the function
			3. break, continue, return - finally executes
		
		A finally clause is always executed before leaving the try statement.
		When an exception has occurred in the try clause and has not been handled by an except clause
		(or it has occurred in a except or else clause), 
		it is re-raised after the finally clause has been executed. 
		The finally clause is also executed “on the way out” 
		when any other clause of the try statement is left via a break, continue or return statement. 
		
		You can leave the except clause with raise, return, break, or continue.
		In any case, the finally clause will execute.
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
	smem_timestamp[TIME_KILLED] = time.time()
	plt.close()
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
	plt.ion()
	plt.show()
	plt.draw()
	plt.pause(.001)

def main():
	try:
		getCLIargs()
		jlog.setup(verbose, quiet)
		jlog.info('gcs: starting')

		#if args.process == 'awacs':
		#	smem_timestamp[TIME_PHOTO] = time.time()
		if process == 'skate':
			smem_timestamp[TIME_AWACS_READY] = time.time()
			smem_timestamp[TIME_PHOTO] = time.time()

		startup()

		startUI()

		# main loop - wait here until everybody ready
		while not smem_timestamp[TIME_SKATE_READY] and not smem_timestamp[TIME_AWACS_READY] and not smem_timestamp[TIME_KILLED]:
			time.sleep(.1)
		smem_timestamp[TIME_READY] = time.time()

		# main loop
		for i in range(60):
			#jlog.info('gcs: is startUI blocking')
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
		jlog.error(f'gcs: main exception: {ex}')
		#jlog.error(traceback.format_exc())
		#raise

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
	#parser.add_argument('-ns' ,'--nosave'                     ,action='store_true'        ,help='suppress save image to disk'      )
	#parser.add_argument('-id' ,'--ssid'                       ,default=rdef.ssid          ,help='network ssid'                     )
	#parser.add_argument('-pw' ,'--sspw'                       ,default=rdef.sspw          ,help='network password'                 )
	#parser.add_argument('-cu' ,'--camurl'                     ,default=rdef.camurl        ,help='URL of camera webserver'          )
	#parser.add_argument('-if' ,'--imgdir'                     ,default=rdef.imgdir        ,help='folder for saveing images'        )
	#parser.add_argument('-fs' ,'--framesize'      ,type=int   ,default=rdef.framesize     ,help='camera framesize'                 )
	#parser.add_argument('-qu' ,'--quality'        ,type=int   ,default=rdef.quality       ,help='camera quality'                   )
	#parser.add_argument('-mc' ,'--numcones'       ,type=int   ,default=rdef.numcones      ,help='number of cones in the arena'     )

	awacs.setupArgParser(parser)

	args = parser.parse_args()	# returns Namespace object, use dot-notation
	
	awacs.args = args

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
	awacs.ssid	= args.ssid
	awacs.sspw	= args.sspw 
	awacs.camurl	= args.camurl
	awacs.framesize	= args.framesize
	awacs.quality	= args.quality
	awacs.imgdir	= args.imgdir
	awacs.numcones	= args.numcones

if __name__ == '__main__':
	main()

