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
import numpy as np
import os

import jlog
from smem import *
import awacs
import skate
import specs

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

# global constants
fps = 2
ui_delay = 1/fps

# global variables
args	= None
awacs_process = False
skate_process = False

# shared memory
smem_timestamp = multiprocessing.Array('d', TIME_ARRAY_SIZE) # initialized with zeros
smem_positions = multiprocessing.Array('i', POS_ARRAY_SIZE)  # initialized with zeros

def kill(msg):
	jlog.info(f'kill: {msg}')
	smem_timestamp[TIME_KILLED]  = time.time()

def startAwacs():
	global awacs_process
	awacs_process = multiprocessing.Process(target=awacs.awacs_main, args=(smem_timestamp, smem_positions))
	awacs_process.start()

def startSkate():
	global skate_process
	skate_process = multiprocessing.Process(target=skate.skate_main, args=(smem_timestamp, smem_positions))
	skate_process.start()

def startProcesses():
	if args.process == 'awacs' or args.process == 'both':
		startAwacs()
	if args.process == 'skate' or args.process == 'both':
		startSkate()

def stopProcesses():
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
		kill('q keyed on UI')
	
def startUI():
	global bow, stern, incr, skateline

	#skateline = plt.gca().scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])
	#bow = np.array([1000,1000])
	#stern = np.array([1200,1200])
	#incr = np.array([20,20])
	
	color = 'black'
	plt.xlim(0,600)
	plt.ylim(0,600)
	plt.autoscale(False)
	plt.gca().set_aspect('equal', anchor='C')
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	plt.gca().spines['bottom'].set_color(color)
	plt.gca().spines['top'].set_color(color)
	plt.gca().spines['left'].set_color(color)
	plt.gca().spines['right'].set_color(color)
	
	plt.ion()
	plt.show()
	fig = plt.gcf()

	running = True

#	def onpress(event):
#		nonlocal running
#		if event.key == 'q': running = False
	fig.canvas.mpl_connect('key_press_event', on_press)

#	for framenum in range(100):  # max framenums  ??
#		animate(framenum)
#		plt.pause(delay)
#		if not running: break

def refreshUI():
	# plot cones
	numcones = smem_positions[NUM_CONES]
	pos = CONE1_X
	for i in range(numcones):
		x,y = specs.awacs2gcs([smem_positions[pos], smem_positions[pos+1]])
		#circle1 = plt.Circle((x, y), 10, color='y')
		#plt.gca().add_patch(circle1)
		plt.text(x, y, str(i+1), fontsize='12', ha='center', va='center', color='black')
		pos += 2

	# plot donut
	x,y = specs.awacs2gcs([smem_positions[DONUT_X], smem_positions[DONUT_Y]])
	circle1 = plt.Circle((x, y), 10, color='r')
	plt.gca().add_patch(circle1)

	# plot skate
	circle1 = plt.Circle((x, y), 5, color='b')
	plt.gca().add_patch(circle1)



#def animate(framenum):
#	global bow,stern,incr, skateline
#	bow += incr
#	stern += incr
#	points = drawSkate(bow,stern,5)
#	skateline.set_offsets(points) # FuncAnimation does the drawing
#
#def drawSkate(bow, stern, n):
#	diff = (bow - stern) / n
#	points = []
#	for i in range(n): points.append(stern + (diff * i))
#	return points
	
def main():
	try:
		getArgs()
		jlog.setup('gcs  ', args.verbose, args.quiet)
		jlog.info(f'starting process id: {os.getpid()}, {time.strftime("%Y%m%d-%H%M%S")}, ui_delay:{ui_delay}')

		# fake timestamps for testing one process at a time
		#if args.process == 'awacs':
		#	smem_timestamp[TIME_PHOTO] = time.time()
		if args.process == 'skate':
			smem_timestamp[TIME_AWACS_READY] = time.time()
			smem_timestamp[TIME_PHOTO] = time.time()

		startProcesses()

		startUI()
		refreshUI()

		# wait here until everybody ready
		while not (smem_timestamp[TIME_SKATE_READY] and smem_timestamp[TIME_AWACS_READY]):
			if smem_timestamp[TIME_KILLED]:
				raise Exception('killed before ready')
			time.sleep(.1)
		smem_timestamp[TIME_READY] = time.time()
		jlog.info('all ready')

		# main loop
		for i in range(25):
			if smem_timestamp[TIME_KILLED]:
				jlog.info('stopping due to kill')
				break;
			refreshUI()
			plt.pause(ui_delay)
			jlog.info(f'loop {i}')

		jlog.debug('fall out of main loop')

	except KeyboardInterrupt:
		kill('keyboard interrupt')
		return
	except Exception as ex:
		kill(f'main exception: {ex}')
		if (args.verbose):
			jlog.error(traceback.format_exc())
	finally:
		# shutdown
		try:
			kill('shutdown finally')
			stopProcesses()
			fig = plt.gcf()
			fig.canvas.print_png('printfile.png')
			plt.close()
		except Exception as ex:
			jlog.info(f'shutdown exception: {ex}')
		jlog.info(f'main exit')

if __name__ == '__main__':
	main()

