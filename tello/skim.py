''' sim.py - sk8 simulator '''
import cv2 as cv
import numpy as np

create all objects

sim mode vs fly mode

while True
	processFrame

shutdown

if __name__ == '__main__':
	wakeup()
	action()
	sleep()

def wakeup():
	visualcortex = vc.VisualCortex()
	hippocampus = hc.Hippocampus()
	hippocampus.start()
	frontalcortex = fc.FrontalCortex()
	neck = nek.Neck()
	eeg = Eeg(visualcortex=visualcortex, hippocampus=hippocampus, frontalcortex=frontalcortex, neck=neck)

def sensoryMotorCircuit():
	# start sensory-motor circuit

	# eyes receive frame from camera socket

	fname = '/home/john/sk8/bench/testcase/frame/6.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
		quit()

	# frame sent to visual cortex for edge detection

	objs = visualcortex.detectObjects(frame)
	print(*objs, sep='\n')

	# ears (cerebrum) receive telemetry data from sensors 
	
	# frame and telemetry data are sent to hippocampus for spatial orientation
	mapp = hippocampus.buildMap(objs)	
	hippocampus.stop()
	print(mapp)
	print(*objs, sep='\n')  # objects list has been scrubbed

	# test display of a single frame
	eeg.scan()
	# for more detailed testing of a stream of frames, see sim.py

def action():
	while True
		vision()
		sensoryMotorCircuit()

if __name__ == '__main__':
	# run a drone simulator
	uni.configureLogging('sim')
	logging.debug('')
	logging.debug('')

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

	# input simulator data
	dirframe = f'{dir}/frame'
	missiondatainput  = f'{dir}/mission.log'
	missiondata = None
	try:	
		fh = open(missiondatainput)
		missiondata = fh.readlines()
		lastline = len(missiondata)
		logging.info('mission log found')
	except:
		logging.info('mission log not found')

	# start as simulator
	hippocampus = Hippocampus(ui=True, save_mission=False)
	hippocampus.start()
	framenum = 1
	dline = None
	while True:
		# read one line from the mission log, optional
		#if fh:
		#	line = fh.readline()
		#	m = re.search( r';fn:(.*?);', line)
		#	framenum = m.group(1)
		if missiondata:
			sline = missiondata[framenum-1]	
			dline = uni.unpack(sline)

		# read the frame
		fname = f'{dirframe}/{framenum}.jpg'
		frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
		if frame is None:
			logging.error(f'file not found: {fname}')
			break;

		# process the frame
		ovec = hippocampus.processFrame(frame, framenum, dline)

		# kill switch
		k = cv.waitKey(1)  # in milliseconds, must be integer
		if k & 0xFF == ord('n'):
			if framenum < lastline:
				framenum += 1
			continue
		elif k & 0xFF == ord('p'):
			if framenum > 1:
				framenum -= 1
			continue
		elif k & 0xFF == ord('r'):
			continue
		elif k & 0xFF == ord('s'):
			self.saveTrain()
			continue
		elif k & 0xFF == ord('0'):
			hippocampus.reopenUI(0)
			continue
		elif k & 0xFF == ord('1'):
			hippocampus.reopenUI(1)
			continue
		elif k & 0xFF == ord('2'):
			hippocampus.reopenUI(2)
			continue
		elif k & 0xFF == ord('3'):
			hippocampus.reopenUI(3)
			continue
		elif k & 0xFF == ord('q'):
			break;

	hippocampus.stop()

