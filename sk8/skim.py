''' skim.py - sk8 simulator '''

import cv2 as cv
import numpy as np
import os
import logging
import universal as uni
import visualcortex as vc
import hippocampus as hc
import frontalcortex as fc
import neck as nek
import eeg as eg

class Skim:
	save_nth = 1
	dirout = '/home/john/sk8/bench/train'

	def __init__(self):
		self.visualcortex = False
		self.hippocampus = False
		self.frontalcortex = False
		self.neck = False
		self.eeg = False

	def wakeup(self):
		uni.configureLogging('sim')
		logging.info('good morning')
		logging.info(f'sim run {uni.sday} {uni.stime}')
	
		# reconstitute the brain parts
		self.visualcortex = vc.VisualCortex()
		self.hippocampus = hc.Hippocampus()
		self.frontalcortex = fc.FrontalCortex()
		self.neck = nek.Neck()
		self.eeg = eg.Eeg(visualcortex=self.visualcortex, hippocampus=self.hippocampus, frontalcortex=self.frontalcortex, neck=self.neck)
	
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
		
		# frame and telemetry data are sent to hippocampus for spatial orientation
		self.hippocampus.buildMap(objs,framenum)	
	
		# display
		keypress = self.eeg.scan()
		return keypress
	
	def openeyes(self):
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
		dir = '/home/john/sk8/bench/train'

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
	
	def vision(self,missiondata,framenum,lastframe,dirframe):
		# read one line from the mission log, optional
		if missiondata:
			sline = missiondata[framenum-1]	
			dline = uni.unpack(sline)
	
		# read the frame
		fname = f'{dirframe}/{framenum}.jpg'
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
	
if __name__ == '__main__':
	skim = Skim()
	skim.wakeup()
	skim.act()
	skim.sleep()

