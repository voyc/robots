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
	hippocampus.start()
	frontalcortex = fc.FrontalCortex()
	neck = nek.Neck()
	eeg = eg.Eeg(visualcortex=visualcortex, hippocampus=hippocampus, frontalcortex=frontalcortex, neck=neck)

def action():
	missiondata,framenum,lastframe,dirframe = openeyes()
	while True:
		frame = vision(missiondata,framenum,lastframe,dirframe)
		if frame is None:
			break
		sensoryMotorCircuit(frame,framenum)
		killed,framenum = checkKillSwitch(framenum,lastframe)
		print(killed,framenum)
		if killed:
			break

def sleep():
	hippocampus.stop()

def sensoryMotorCircuit(frame,framenum):
	# start sensory-motor circuit

	objs = visualcortex.detectObjects(frame)

	# ears (cerebrum) receive telemetry data from sensors 
	
	# frame and telemetry data are sent to hippocampus for spatial orientation
	mapp = hippocampus.buildMap(objs)	

	# display
	eeg.scan()

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
	print(f'in vision {framenum}')
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

def checkKillSwitch(framenum,lastframe):
	kill = False
	k = cv.waitKey(0)  # in milliseconds, must be integer
	if k & 0xFF == ord('n'):
		if framenum < lastframe:
			framenum += 1
	elif k & 0xFF == ord('p'):
		if framenum > 1:
			framenum -= 1
	elif k & 0xFF == ord('r'):
		pass
	elif k & 0xFF == ord('s'):
		self.saveTrain()
	elif k & 0xFF == ord('0'):
		hippocampus.reopenUI(0)
	elif k & 0xFF == ord('1'):
		hippocampus.reopenUI(1)
	elif k & 0xFF == ord('2'):
		hippocampus.reopenUI(2)
	elif k & 0xFF == ord('3'):
		hippocampus.reopenUI(3)
	elif k & 0xFF == ord('q'):
		kill = True
	return kill,framenum

if __name__ == '__main__':
	wakeup()
	action()
	sleep()

