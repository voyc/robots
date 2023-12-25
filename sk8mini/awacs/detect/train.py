' train.py - training' 
import os
import copy
import cv2
import numpy as np
import csv
import pdb

# one training set and three tests
ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/training/loop/'
itrainsufx = '_train.csv'

def inRange( a, lower, upper):
	return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

def detectObjects(img,model,cls):
	mod = model[cls]

	p = mod['spec']
	lower = np.array([p[0]['value'], p[2]['value'], p[4]['value']])
	upper = np.array([p[1]['value'], p[3]['value'], p[5]['value']])
	imgMask = cv2.inRange(img,lower,upper)

	contours, _ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

	#qualify by size
	sz = mod['size']
	lowerSize = np.array([sz[0][0], sz[1][0]])
	upperSize = np.array([sz[0][1], sz[1][1]])

	qcnt = 0
	detected = []
	for cnt in contours:

		if False:
			rect = cv2.minAreaRect(cnt) 
			size = rect[1]
		else:
			bbox = cv2.boundingRect(cnt)
			x, y, w, h = bbox
			size = np.array([w,h])
		
		if inRange(size, lowerSize, upperSize):
			qcnt += 1
			detected = bbox

	print(f'contours found: {len(contours)}, qualified by size: {qcnt}')
	return detected

def readDetect(fname):
	with open(fname) as f:
		contents = csv.reader(f)
		train = list(contents)
		train = np.intp(train)
	return train

def showDetect(image,detect):
	img = copy.deepcopy(image)
	for obj in detect:
		l = obj[1]
		t = obj[2]
		w = obj[3]
		h = obj[4]
		r = l + w
		b = t + h
		box = np.array([[l,t], [r,t], [r,b], [l,b]])
		cv2.drawContours(img, [box], 0, (0,0,255),1)
	cv2.imshow('test', img)
	cv2.waitKey(0)


def scoreFolder(model,folder, cls):
	total_score = 0
	for filename in os.listdir(folder):
		basename, ext = os.path.splitext(filename)
		if ext == '.jpg':
			print(f'open image {filename}')
			img = cv2.imread(ifolder+filename, cv2.IMREAD_UNCHANGED)
			train = readDetect(ifolder+basename+itrainsufx)
			detect = detectObjects(img,model,cls)
			score = len(detect)  #score = score(train,detect)
			total_score += score
	
	return total_score

# model, fixed, read from disk, one model per folder
model = {
1:{
'cls':1,
'name':'cone',
'spec':[
	{'name':'hue_min', 'value': 23, 'lower':0, 'upper':255, 'way':+1, 'incr':[80,10,1]},
	{'name':'hue_max', 'value': 37, 'lower':0, 'upper':255, 'way':-1, 'incr':[80,10,1]},
	{'name':'sat_min', 'value':114, 'lower':0, 'upper':255, 'way':+1, 'incr':[80,10,1]},
	{'name':'sat_max', 'value':225, 'lower':0, 'upper':255, 'way':-1, 'incr':[80,10,1]},
	{'name':'val_min', 'value': 57, 'lower':0, 'upper':255, 'way':+1, 'incr':[80,10,1]},
	{'name':'val_max', 'value':205, 'lower':0, 'upper':255, 'way':-1, 'incr':[80,10,1]},
],
'size': [[20,40], [20,40]]
},
2:{
'cls':2,
'name':'sk8',
'spec':[
	{'name':'hue_min', 'value':  0, 'lower':0, 'upper':255, 'way':+1, 'incr':[80,10,1]},
	{'name':'hue_max', 'value': 17, 'lower':0, 'upper':255, 'way':-1, 'incr':[80,10,1]},
	{'name':'sat_min', 'value':117, 'lower':0, 'upper':255, 'way':+1, 'incr':[80,10,1]},
	{'name':'sat_max', 'value':195, 'lower':0, 'upper':255, 'way':-1, 'incr':[80,10,1]},
	{'name':'val_min', 'value': 47, 'lower':0, 'upper':255, 'way':+1, 'incr':[80,10,1]},
	{'name':'val_max', 'value':128, 'lower':0, 'upper':255, 'way':-1, 'incr':[80,10,1]},
],
'size': [[15, 45], [30, 90]]
}}

# schedule, working variable, created once for each class.spec
schedule = [  # shown here as created from one class in the above model
	{'value':  0, 'inc':+10, 'start':  0, 'limit':255, 'prec':0 },
	{'value':255, 'inc':-10, 'start':255, 'limit':  0, 'prec':0 }, 
	{'value':  0, 'inc':+10, 'start':  0, 'limit':255, 'prec':0 },
	{'value':255, 'inc':-10, 'start':255, 'limit':  0, 'prec':0 }, 
	{'value':  0, 'inc':+10, 'start':  0, 'limit':255, 'prec':0 },
	{'value':255, 'inc':-10, 'start':255, 'limit':  0, 'prec':0 }, 
]
# set these in createSchedule
skn = len(schedule)  # number of param in the schedule
skdepth = 0            # index into schedule

# bump one parameter, traverse the nested loop tree
def bumpSchedule():
	global schedule, skdepth, skn
	def incrValue(value, inc, limit):
		value += inc
		pastlimit = (inc > 0 and value > limit) or (inc < 0 and value < limit)
		return value, pastlimit
		
	rc = True
	sc = schedule[skdepth]
	newvalue, pastlimit = incrValue(sc['value'], sc['inc'], sc['limit'])  # do the bump
	if pastlimit:
		sc['value'] = sc['start']
		skdepth -= 1  # back out
		if skdepth < 0:
			rc = False  # training is finished
	else:
		sc['value'] = newvalue
		if skdepth + 1 < skn:
			skdepth += 1  # dig down
		
	return rc


def createSchedule(model, cls):
	global schedule, skdepth, skn   # four outputs
	spec = model[cls]['spec']   # input spec, schedule built one for one

	del schedule[:]
	for ndx in range(0,len(spec)):
		sp = spec[ndx]
		sc = {}
		if sp['way'] > 0:
			sc['value'] = sp['lower']
			sc['start'] = sp['lower']
			sc['limit'] = sp['upper']
		else:
			sc['value'] = sp['upper']
			sc['start'] = sp['upper']
			sc['limit'] = sp['lower']
		sc['prec'] = 0
		sc['inc'] = sp['incr'][sc['prec']] * sp['way'] 
		schedule.append(sc)

	skn = len(schedule)
	skdepth = 0
	return

def trainModel(folder, cls):
	global schedule, skdepth, skn
	print(f'open model for {folder}')
	print(model, end='\n\n')

	createSchedule(model,1)
	print(schedule, end='\n\n')

	print('go', end=' ')
	training = True
	while training:
		print( skdepth, end='')
		#score = scoreFolder(model, folder, cls)
		training = bumpSchedule()
	print(' done')

	#writeModel(fname, model)
	print(schedule, end='\n\n')

def main():
	trainModel(ifolder, 1)
	quit()

main()
