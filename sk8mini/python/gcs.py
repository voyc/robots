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

def getArgs(): # get command-line arguments 
	global args
	parser = argparse.ArgumentParser()
	parser.add_argument('--verbose'  ,action='store_true'  ,help='verbose comments'                 ) 
	parser.add_argument('--quiet'    ,action='store_true'  ,help='suppress all output'              )
	parser.add_argument('--process'  ,default='both'       ,help='process: both,skate,awacs,none'   )

	awacs.setupArgParser(parser)
	skate.setupArgParser(parser)
	args = parser.parse_args()	# returns Namespace object, use dot-notation
	awacs.args = args
	skate.args = args

# global variables
args	= None
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
	if args.process == 'awacs' or args.process == 'both':
		startAwacs()
	if args.process == 'skate' or args.process == 'both':
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
		getArgs()
		jlog.setup(args.verbose, args.quiet)
		jlog.info('gcs: starting')

		# fake timestamps for testing one process at a time
		#if args.process == 'awacs':
		#	smem_timestamp[TIME_PHOTO] = time.time()
		if args.process == 'skate':
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

if __name__ == '__main__':
	main()

