''' skim.py - sk8 simulator '''

import sys
import os
import cv2 as cv
import numpy as np
import logging
import universal as uni
import visualcortex as vc
import hippocampus as hc
import frontalcortex as fc
import eeg as eg
import drone as drn

class Skim:
	save_nth = 1
	dirout = '/home/john/sk8/bench/train'
	max_mission_time = 60*60*24

	def __init__(self,dirsim):
		self.dirsim = dirsim
		self.visualcortex = False
		self.hippocampus = False
		self.frontalcortex = False
		self.eeg = False

	def wakeup(self):
		uni.configureLogging('sim')
		logging.info('good morning')
		logging.info(f'sim run {uni.sday} {uni.stime}')
		logging.info(f'input {self.dirsim}')
	
		# reconstitute the brain parts
		self.visualcortex = vc.VisualCortex()
		self.hippocampus = hc.Hippocampus()
		self.frontalcortex = fc.FrontalCortex(self.max_mission_time)
		self.drone = drn.Drone(False)
		self.eeg = eg.Eeg(visualcortex=self.visualcortex, hippocampus=self.hippocampus, frontalcortex=self.frontalcortex, drone=self.drone)
	
		if self.save_nth:
			self.dirframeout = f'{self.dirout}/frame'
			self.dirtrainout = f'{self.dirout}/train'
			self.framenumout = self.getNextFrameNum(self.dirframeout)

	def getNextFrameNum(self,dirname):
		filelist = os.listdir( dirname)
		hnum = 0
		for fname in filelist: 
			fbase = os.path.splitext(fname)[0]
			num = int(fbase) 
			if num > hnum:
				hnum = num
		hnum += 1
		return hnum
	
	def act(self):
		missiondata,framenum,lastframe,dirframe = self.openeyes()
		while True:
			frame = self.vision(missiondata,framenum,lastframe,dirframe)
			if frame is None:
				framenum -= 1
				continue
	
			keypress = self.sensoryMotorCircuit(frame,framenum)
			killed,framenum = self.handleKeypress(keypress,framenum,lastframe)
			if killed:
				break
	
	def sleep(self):
		logging.info('sleep tight')
	
	def sensoryMotorCircuit(self,frame,framenum):
		objs = self.visualcortex.detectObjects(frame,vc.Detect.threshhold_seeds)
		self.frame = frame
		self.objs = objs
	
		# ears (cerebrum) receive telemetry data from sensors 
		
		fmap, posts = self.hippocampus.buildMap(objs,framenum)	
	
		vector = self.frontalcortex.navigate(self.drone.state, fmap, drn.max_mmo)

		if vector:
			rccmd = self.drone.go(vector)
	
		# display
		keypress = self.eeg.scan()
		return keypress
	
	def openeyes(self):
		dirframe = f'{self.dirsim}/frame'
		missiondatainput  = f'{self.dirsim}/mission.log'
	
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
	
	def vision(self,missiondata,framenum,lastframe,dirframe):
		# read one line from the mission log, optional
		if missiondata:
			sline = missiondata[framenum-1]	
			dline = uni.unpack(sline)
			fn = dline['fn']
		else:
			fn = framenum
	
		# read the frame
		fname = f'{dirframe}/{fn}.jpg'
		frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
		if frame is None:
			logging.error(f'file not found: {fname}')
			return None
		return frame
	
	def handleKeypress(self,keypress,framenum,lastframe):
		kill = False
		newframe = framenum
		if keypress == 'n' and framenum < lastframe:
			newframe += 1
		elif keypress == 'p' and framenum > 1:
			newframe -= 1
		elif keypress == 'r':
			pass
		elif keypress == 's':
			self.log()
		elif keypress == 'q':
			kill = True
		elif keypress in ['0','1','2','3']:
			visualcortex.switchFocus(int)
		return kill,newframe
	
	def log(self):
		# save frame
		fname = f'{self.dirframeout}/{self.framenumout}.jpg'
		cv.imwrite( fname, self.frame)
	
		# save training data
		fname = f'{self.dirtrainout}/{self.framenumout}.txt'
		f = open(fname, 'a')
		for obj in self.objs:
			f.write(obj.write())
		f.close()
		self.framenumout += 1

def latest(dirbase):
	group = 'fly'
	sdate = sorted(os.listdir(f'{dirbase}/{group}/'))[-1]
	stime = sorted(os.listdir(f'{dirbase}/{group}/{sdate}'))[-1]
	return f'{dirbase}/{group}/{sdate}/{stime}/'
	
if __name__ == '__main__':
	dirbase = '/home/john/sk8'
	dirsim = f'{dirbase}/bench/train'
	if len(sys.argv) > 1:
		dirsim = f'{dirbase}/{sys.argv[1]}'
	else:
		dirsim = latest(dirbase)
	
	skim = Skim(dirsim)
	skim.wakeup()
	skim.act()
	skim.sleep()

'''
historic test flights
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

	dir = '/home/john/sk8/bench/train_padv1'
	dir = '/home/john/sk8/fly/20210601/115432'  # new pad, height levels, 24-frame anomoly at 3282
	dir = '/home/john/sk8/bench/train'          # nn training data
	dir = '/home/john/sk8/fly/20210607/112940'
'''
