''' 
train.py - training

one folder represents one training set
the folder contains one model and multiple jpg images
each jpg image has a matching training file, 
matched by filename, like 00001.jpg and 00001_train.csv
''' 
import os
import copy
import cv2
import numpy as np
import csv
import json
import argparse
import logging

import lib.model


# used for both schedule and model
def prettyPrint(json_dict):
	s = json.dumps(json_dict)
	s = s.replace('[{','[\n{')
	s = s.replace('}, ','},\n')
	return s

def formatSchedule(nloop, schedule):
	s = f'{nloop}: '
	for sc in schedule:
		s += str(sc['sp']['value'])
		s += ':' if (sc['inc']>0)  else ', '
	return s

#--------------- detect ---------------------------------------------------------#

# used within detectObjects
def inRange( a, lower, upper):
	return np.greater_equal(a, lower).all() and np.less_equal(a, upper).all()

def detectObjects(img,model,cls):
	mod = model[cls]

	# algo 1 hsv
	sp = mod['spec']
	lower = np.array([sp[0]['value'], sp[2]['value'], sp[4]['value']])
	upper = np.array([sp[1]['value'], sp[3]['value'], sp[5]['value']])
	imgMask = cv2.inRange(img,lower,upper)

	print(lower, upper)

	contours, _ = cv2.findContours(imgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
	if len(contours) > 3:
		breakpoint()

	#qualify by size
	sz = mod['size']
	lowerSize = np.array([sz[0][0], sz[1][0]])
	upperSize = np.array([sz[0][1], sz[1][1]])

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
			detected.append(bbox)

	print(f'contours found: {len(contours)}, qualified by size: {len(detected)}')
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

#--------------- score ---------------------------------------------------------#

def scoreFolder(model,folder, cls):
	total_score = 0
	for filename in os.listdir(folder):
		basename, ext = os.path.splitext(filename)
		if ext == '.jpg':
			#print(f'open image {filename}')
			img = cv2.imread(ifolder+filename, cv2.IMREAD_UNCHANGED)
			train = readDetect(ifolder+basename+itrainsufx)
			detect = detectObjects(img,model,cls)
			score = len(detect)  #score = score(train,detect)
			total_score += score
	
	return total_score

#--------------- training ----------------------------------------------#

def trainModel(model, cls, level):
	example_schedule = [
		{'inc':+10, 'start':  0, 'limit':255, 'sp':{}},
		{'inc':-10, 'start':255, 'limit':  0, 'sp':{}}, 
		{'inc':+10, 'start':  0, 'limit':255, 'sp':{}},
		{'inc':-10, 'start':255, 'limit':  0, 'sp':{}}, 
		{'inc':+10, 'start':  0, 'limit':255, 'sp':{}},
		{'inc':-10, 'start':255, 'limit':  0, 'sp':{}}, 
	]


	def createSchedule(model, cls, level):
		spec = model[cls]['spec']   # input spec, schedule built one for one
		sched = []
		for ndx in range(0,len(spec)):
			sp = spec[ndx]
			sc = {}
			if sp['way'] > 0:
				#sc['sp']['value'] = sp['lower']  # already done in initializeModel()
				sc['start'] = sp['lower']
				sc['limit'] = sp['upper']
			else:
				#sc['sp']['value'] = sp['upper']
				sc['start'] = sp['upper']
				sc['limit'] = sp['lower']
			sc['inc'] = sp['incr'][level] * sp['way'] 
			sc['sp'] = sp
			sched.append(sc)
		return sched

	def bumpSchedule():
		nonlocal schedule, skdepth
		stillTraining = True
		stillBumping = True
		while stillTraining and stillBumping:
			sc = schedule[skdepth]
			newvalue = sc['sp']['value'] + sc['inc']
	
			isPastLimit = (sc['inc'] > 0 and newvalue > sc['limit']) or (sc['inc']<0 and newvalue < sc['limit'])
		
			psc = schedule[skdepth-1]
			isPastLower = sc['inc'] < 0 and newvalue < psc['sp']['value']
				
			if isPastLimit or isPastLower: # done with this depth
				sc['sp']['value'] = sc['start']
				skdepth -= 1  # back out
				if skdepth < 0:
					stillTraining = False
			else:
				sc['sp']['value'] = newvalue
				skdepth = len(schedule)-1
				stillBumping = False
			
		return stillTraining

	schedule = createSchedule(model, cls, level)
	skdepth = len(schedule)-1
	logging.info(f"create schedule for {model[cls]['cls']}, {model[cls]['name']}, level:{level}")
	logging.info(prettyPrint(schedule))

	low_score = float('inf')
	best_model = {}

	training = True
	nloop = 1
	while training:
		logging.info(formatSchedule(nloop, schedule))
		if args.paging and not nloop % 50:
			breakpoint()

#		#print( skdepth, end='', flush=True)
#		score = scoreFolder(model, folder, cls)
#		#print(f'score:{score}')
#
#		if score < low_score:
#			low_score = score
#			#print(f'low score: {low_score}')
#			# move all values from schedule to model	
#			spec = model[cls]['spec']
#			for n in range(skn):
#				spec[n]['value'] = schedule[n]['value']
#
#			# move the schedule values to the model
#				
#			best_model = copy.deepcopy(model)
		training = bumpSchedule()
		nloop += 1

	prettyPrint(best_model)

#--------------- main ----------------------------------------------#

def main():
	global args

	# get command-line parameters 
	example_folder = '/home/john/media/webapps/sk8mini/awacs/photos/training/loop/'
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=example_folder                                     ,help='input folder.'                                              ),
	parser.add_argument('-im' ,'--imodel'         ,default='model.json'                                       ,help='input model filename.'                                      ),
	parser.add_argument('-om' ,'--omodel'         ,default='newmodel.json'                                    ,help='output model filename. default to input model.'             ),
	parser.add_argument('-ia' ,'--iimagesufx'     ,default='.jpg'                                             ,help='input image filename suffix.'                               ),
	parser.add_argument('-it' ,'--itrainsufx'     ,default='_train.csv'                                       ,help='input train filename suffix.'                               ),
	parser.add_argument('-c'  ,'--cls'            ,default='all'                                              ,help='name of classifier to be processed. default to "all".'      ),
	parser.add_argument('-l'  ,'--level'          ,default='all'                                              ,help='name of classifier to be processed. default to "all".'      ),
	parser.add_argument('-s'  ,'--scratch'        ,default=True                 ,action='store_false'         ,help='start from scratch (default).'                              ),
	parser.add_argument('-v'  ,'--verbose'        ,default=False                ,action='store_true'          ,help='display additional output messages.'                        ),
	parser.add_argument('-q'  ,'--quiet'          ,default=False                ,action='store_true'          ,help='suppresses all output.'                                     ),
	parser.add_argument('-p'  ,'--paging'         ,default=False                ,action='store_true'          ,help='breakpoint every 50 iterations.'                            ),
	args = parser.parse_args()	# returns Namespace object, use dot-notation

	# logging
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if args.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if args.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(args)

	# get model
	model = lib.model.read(os.path.join(args.ifolder, args.imodel))
	if args.scratch:
		lib.model.initialize(model,args.cls)
	best_model = copy.deepcopy(model)
	for cls in model:
		modcls = model[cls]
		logging.info(f"{modcls['cls']}, {modcls['name']}, {len(modcls['spec'])} params, {len(modcls['spec'][0]['incr'])} levels")

	# loop thru cls : level
	for cls in model:
		if args.cls != 'all' and args.cls != cls:
			continue
		modcls = model[cls]
		spec = modcls['spec']
		sp = spec[0]
		numlevels = len(sp['incr'])
		for level in range(numlevels):
			if args.level != 'all' and int(args.level) != level:
				continue
			trainModel(model, cls, level)

	#write best model
	#writeModel(fname, model)

if __name__ == "__main__":
	main()
