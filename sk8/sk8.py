''' sk8.py - control sk8 robot '''

import cv2 as cv
import numpy as np
import logging
import universal as uni
import visualcortex as vc
import hippocampus as hc
import frontalcortex as fc
import neck as nek
import drone as drn

def yahoo(data,count):
	pass

drone = False

def wakeup():
	global drone

	uni.configureLogging('fly')
	logging.info('good morning')

	# reconstitute the brain parts
	global hippocampus,visualcortex,frontalcortex,neck,eeg
	visualcortex = vc.VisualCortex()
	hippocampus = hc.Hippocampus()
	hippocampus.start()
	frontalcortex = fc.FrontalCortex()
	neck = nek.Neck()
	drone = drn.Drone(yahoo,sensoryMotorCircuit)

def act():
	started = drone.prepareForTakeoff()
	if started:
		logging.info('start mission')
		drone.wait()  # block here until video and telem threads stopped

def sleep():
	logging.info('good night')

def sensoryMotorCircuit(frame,framenum):
	objs = visualcortex.detectObjects(frame)
	hippocampus.buildMap(objs,framenum)	
	vector = frontalcortex.navigate()
	if not vector:
		drone.stop()
	else:
		rccmd = uni.composeRcCommand(vector)
		#drone.cmd.sendCommand(rccmd)
	return

if __name__ == '__main__':
	wakeup()
	act()
	sleep()

