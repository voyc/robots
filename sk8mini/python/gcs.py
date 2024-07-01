''' 
gcs.py  ground control station

runs on laptop
no longer useful
	it used to do more, but now all functions have been offloaded to skate and awacs

software architecture:
	see https://curriculum.voyc.com/doku.php?id=python#software_architecture_options 

	we decided to use the multiprocessing library to implement 3 processes:
		gcs - 
			get runtime options from the command line
			allocate shared data: mapped in smem.py 
			start two child processes: skate and awacs
			setup shared memory
			kill on Ctrl-C

		awacs - camera and CV
			take photos
			georeference to cover arena
			object detection
			download photos and labels from awacs and save to disk for ai training
		
		skate - navigation and piloting
			setup - calibration
			get arena map from awacs
			get position from awacs
			dead reckon position
			command - choose patterns, plan route
			navigate - plot route
			autopilot
			manual piloting - matplotlib keyboard
			visualize arena - matplotlib

how to debug multiprocessing:
	import pdb; pdb.set_trace()  # does not work in child process

python exceptions:
	the purpose of catching an exception, is to prevent the program from interrupting
	so if you want the program to interrupt, you must take action
		1. raise - run the finally clause and then goto outer try
		2. return - run the finally clause and then return from the function
		3. break, continue - run the finally clause, and then what?
	
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
import os

import jlog
from smem import *
import awacs
import skate
import specs

awacs_process = False
skate_process = False

smem_timestamp = None
smem_positions = None

args	= None

def getArgs(): # get command-line arguments 
	global args
	parser = argparse.ArgumentParser()
	parser.add_argument('--verbose'  ,action='store_true'  ,help='verbose comments'                 ) 
	parser.add_argument('--quiet'    ,action='store_true'  ,help='suppress all output'              )
	parser.add_argument('--sim'	 ,action='store_true'  ,help='simulation mode'                  )
	parser.add_argument('--mediaout' ,default='/home/john/media/webapps/sk8mini/awacs/photos' ,help='folder out for images, log')

	awacs.setupArgParser(parser)
	skate.setupArgParser(parser)
	args = parser.parse_args() # returns Namespace object, use dot-notation
	awacs.args = args
	skate.args = args

	args.mediaout = f'{args.mediaout}/{time.strftime("%Y%m%d-%H%M%S")}'
	os.mkdir(args.mediaout)

def main():
	global smem_timestamp, smem_positions, awacs_process, skate_process
	try:
		getArgs()
		jlog.setup('gcs  ', args.verbose, args.quiet, args.mediaout)
		jlog.info(f'starting process id: {os.getpid()}, {time.strftime("%Y%m%d-%H%M%S")}')

		smem_timestamp = multiprocessing.Array('d', TIME_ARRAY_SIZE) # initialized with zeros
		smem_positions = multiprocessing.Array('i', POS_ARRAY_SIZE)  # initialized with zeros

		awacs_process = multiprocessing.Process(target=awacs.awacs_main, args=(smem_timestamp, smem_positions))
		awacs_process.start()

		skate_process = multiprocessing.Process(target=skate.skate_main, args=(smem_timestamp, smem_positions))
		skate_process.start()

		skate_process.join() # wait here to catch KeyboardInterrupt
		awacs_process.join()
		jlog.debug('exit main')

	except KeyboardInterrupt:
		jlog.info(f'keyboard interrupt')
		smem_timestamp[TIME_KILLED]  = time.time()  # causes awacs and skate to end
		return

if __name__ == '__main__':
	main()
	jlog.debug('exit gcs')

