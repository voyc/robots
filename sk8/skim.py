''' skim.py - sk8 simulator '''
import cv2 as cv
import numpy as np
import logging
import universal as uni
import visualcortex as vc
import hippocampus as hc
import frontalcortex as fc
import neck as nek
import eeg as eg

def wakeup():
	uni.configureLogging('sim')
	logging.debug('')
	logging.debug('')

	# reconstitute the brain parts
	global hippocampus,visualcortex,frontalcortex,neck,eeg
	visualcortex = vc.VisualCortex()
	hippocampus = hc.Hippocampus()
	frontalcortex = fc.FrontalCortex()
	neck = nek.Neck()

	eeg = eg.Eeg(visualcortex=visualcortex, hippocampus=hippocampus, frontalcortex=frontalcortex, neck=neck)
	#eeg.openUI()

def act():
	missiondata,framenum,lastframe,dirframe = openeyes()
	while True:
		frame = vision(missiondata,framenum,lastframe,dirframe)
		if frame is None:
			break

		keypress = sensoryMotorCircuit(frame,framenum)
		killed,framenum = handleKeypress(keypress,framenum,lastframe)
		if killed:
			break

def sleep():
	logging.info('sleep tight')

def sensoryMotorCircuit(frame,framenum):
	# start sensory-motor circuit

	objs = visualcortex.detectObjects(frame)

	# ears (cerebrum) receive telemetry data from sensors 
	
	# frame and telemetry data are sent to hippocampus for spatial orientation
	hippocampus.buildMap(objs,framenum)	

	# display
	keypress = eeg.scan()
	return keypress

def openeyes():
	# sim with frames only
	dir = '/home/john/sk8/bench/testcase'        # 1-5
	dir = '/home/john/sk8/bench/20210511-113944' # start at 201
	dir = '/home/john/sk8/bench/20210511-115238' # start at 206
	dir = '/home/john/sk8/bench/aglcalc'         # 15 frames by agl in mm

	# sim with mission log
	dir = '/home/john/sk8/fly/20210512/095147'  # manual stand to two meters
	dir = '/home/john/sk8/fly/20210512/143128' # on the ground with tape measure
	dir = '/home/john/sk8/fly/20210512/161543'  # 5 steps of 200 mm each
	dir = '/home/john/sk8/fly/20210512/212141'  # 30,50,100,120,140,160,180,200 mm
	dir = '/home/john/sk8/fly/20210512/224139'  # 150, 200 mm agl
	dir = '/home/john/sk8/fly/20210514/172116'  # agl calc

	dir = '/home/john/sk8/fly/20210521/091519'

	dirframe = f'{dir}/frame'
	missiondatainput  = f'{dir}/mission.log'

	# mission log, optional
	missiondata = None
	lastframe = 10000000
	framenum = 1
	try:	
		fh = open(missiondatainput)
		missiondata = fh.readlines()
		lastframe = len(missiondata)
		logging.info('mission log found')
	except:
		logging.info('mission log not found')
	return missiondata,framenum,lastframe,dirframe

def vision(missiondata,framenum,lastframe,dirframe):
	# read one line from the mission log, optional
	if missiondata:
		sline = missiondata[framenum-1]	
		dline = uni.unpack(sline)

	# read the frame
	fname = f'{dirframe}/{framenum}.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
	return frame

def handleKeypress(keypress,framenum,lastframe):
	kill = False
	newframe = framenum
	if keypress == 'n' and framenum < lastframe:
		newframe += 1
	elif keypress == 'p' and framenum > 1:
		newframe -= 1
	elif keypress == 'r':
		pass
	elif keypress == 's':
		self.saveTrain()
	elif keypress == 'q':
		kill = True
	elif keypress in ['0','1','2','3']:
		visualcortex.switchFocus(int)
	return kill,newframe

if __name__ == '__main__':
	wakeup()
	act()
	sleep()

