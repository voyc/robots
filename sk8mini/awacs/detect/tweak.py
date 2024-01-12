'''
tweak.py - tweak the model, while detecting objects in images
'''

import numpy as np
import cv2
from datetime import datetime
import sys
import json
import argparse
import logging
import os

import model as mod
import detect
import label as lab
import draw

gspec = None  # dict containing command-line parameters, initialized in main()
gwindow_name = ''

#--------------- manual model initialization, aka "settings" ----------------------------------------# 

def empty(a): # passed to trackbar
	pass

def openSettings(modcls):
	global gwindow_name
	gwindow_name = f'{modcls["name"]} settings'
	cv2.namedWindow( gwindow_name, cv2.WINDOW_NORMAL)
	cv2.resizeWindow(gwindow_name, 1200, 600) 
	specs = modcls['spec']
	for spec in specs:
		name = spec['name']
		value = spec['value']
		upper = spec['upper']
		cv2.createTrackbar(name, gwindow_name, value, upper, empty)

	size = modcls['size']
	for spec in size:
		name = spec['name']
		value = spec['value']
		upper = spec['upper']
		cv2.createTrackbar(name, gwindow_name, value, upper, empty)

def readSettings(modcls):
	specs = modcls['spec']
	for spec in specs:
		spec['value'] = cv2.getTrackbarPos(spec['name'], gwindow_name)
	size = modcls['size']
	for spec in size:
		spec['value'] = cv2.getTrackbarPos(spec['name'], gwindow_name)

#def stackImages(scale,imgArray):
#	rows = len(imgArray)
#	cols = len(imgArray[0])
#	rowsAvailable = isinstance(imgArray[0], list)
#	width = imgArray[0][0].shape[1]
#	height = imgArray[0][0].shape[0]
#	if rowsAvailable:
#		for x in range ( 0, rows):
#			for y in range(0, cols):
#				if imgArray[x][y].shape[:2] == imgArray[0][0].shape [:2]:
#					imgArray[x][y] = cv2.resize(imgArray[x][y], (0, 0), None, scale, scale)
#				else:
#					imgArray[x][y] = cv2.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale, scale)
#				if len(imgArray[x][y].shape) == 2: imgArray[x][y]= cv2.cvtColor( imgArray[x][y], cv2.COLOR_GRAY2BGR)
#		imageBlank = np.zeros((height, width, 3), np.uint8)
#		hor = [imageBlank]*rows
#		hor_con = [imageBlank]*rows
#		for x in range(0, rows):
#			hor[x] = np.hstack(imgArray[x])
#		ver = np.vstack(hor)
#	else:
#		for x in range(0, rows):
#			if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
#				imgArray[x] = cv2.resize(imgArray[x], (0, 0), None, scale, scale)
#			else:
#				imgArray[x] = cv2.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None,scale, scale)
#			if len(imgArray[x].shape) == 2: imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
#		hor= np.hstack(imgArray)
#		ver = hor
#	return ver

#--------------- main loop ----------------------------------------# 

# one image one cls
def processImageClass(img, model, cls):
	req = 'next'
	if gspec.manual:
		logging.debug(cls)
		logging.debug(model[cls])
		openSettings(model[cls])
		while True:
			readSettings(model[cls])
			labels,imgMask = detect.detectObjects(img, model, cls)

			# show the images
			imgAnnotated = draw.drawImage(img,labels)
			stack= np.hstack((img,imgMask, imgAnnotated))
			cv2.imshow(gwindow_name, stack)
			key = cv2.waitKey(1)
			if key & 0xFF == ord('q'):	# quit
				req = 'quit'
				break
			elif key & 0xFF == 13:		# return, next image
				req = 'next'
				break
		cv2.destroyAllWindows()
	else:
		labels,_ = detect.detectObjects(img, model, cls)
	return labels, req

def main():
	global gspec

	example_folder = '/home/john/media/webapps/sk8mini/awacs/photos/20240109-174051/keep/' 
	example_folder = '/home/john/media/webapps/sk8mini/awacs/photos/train3/' 

	#example_image = '00033.jpg'
	#example_model = 'model.json'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=example_folder                                     ,help='input folder.'                                              ),
	parser.add_argument('-of' ,'--ofolder'        ,default=''                                                 ,help='output folder. default to input folder.'                    ),
	parser.add_argument('-ii' ,'--iimage'         ,default='all'                                              ,help='input image filename.'                                      ),
	parser.add_argument('-oi' ,'--oimage'         ,default=''                                                 ,help='output image filename. not in use.'                         ),
	parser.add_argument('-im' ,'--imodel'         ,default='model.json'                                       ,help='input model filename.'                                      ),
	parser.add_argument('-om' ,'--omodel'         ,default='newmodel.json'                                    ,help='output model filename. default to input model.'             ),
	parser.add_argument('-ia' ,'--itruthsufx'     ,default='_truth'                                           ,help='input label filename suffix.'                                   ),
	parser.add_argument('-oa' ,'--olabelsufx'     ,default='_label'                                           ,help='output label filename suffix.'                                  ),
	parser.add_argument('-c'  ,'--cls'            ,default='all'                                              ,help='name of classifier to be processed. default to "all".'      ),
	parser.add_argument('-v'  ,'--verbose'        ,default=False                ,action='store_true'          ,help='display additional output messages.'                        ),
	parser.add_argument('-q'  ,'--quiet'          ,default=False                ,action='store_true'          ,help='suppresses all output.'                                     ),
	parser.add_argument('-m'  ,'--manual'         ,default=False                ,action='store_true'          ,help='let user initialize the model manually'                     ),
	parser.add_argument('-t'  ,'--train'          ,default=False                ,action='store_true'          ,help='train the model.'                                           ),
	gspec = parser.parse_args()	# returns Namespace object, use dot-notation

	# set defaults for missing params
	if gspec.ifolder != '' and gspec.ifolder[len(gspec.ifolder)-1] != '/':
		gspec.ifolder += '/'
	if gspec.ofolder == '':
		gspec.ofolder = gspec.ifolder
	if gspec.oimage == '':
		gspec.oimage = gspec.iimage
	if gspec.omodel == '':
		gspec.omodel = gspec.imodel

	# logging
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if gspec.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if gspec.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(gspec)

	# read model
	fname = gspec.ifolder+gspec.imodel
	model = mod.read(fname)
	logging.info(f'reading model from {fname}')
	logging.debug(model)
	logging.debug(model['1'])

	# loop all images in folder
	req = 'next'
	totalerror = 0
	numfiles = 0
	for filename in os.listdir(gspec.ifolder):
		if gspec.iimage == 'all' or gspec.iimage == filename: 
			basename, ext = os.path.splitext(filename)
			if ext == '.jpg': 
				labels = []
				fname = gspec.ifolder+filename
				img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
				logging.info(f'reading image from {fname}')
				logging.debug(f'image shape: {img.shape}')
				if gspec.train:
					truth = lab.read(gspec.ifolder+basename+gspec.itruthsufx+'.csv')

				# loop classes for in model
				for m in model:
					if gspec.cls == 'all' or gspec.cls == m:
						label,req = processImageClass(img, model, m)
						labels += label
					if req == 'quit':
						break
				if gspec.train:
					error = score.score(truth, labels)
					totalerror += error
					numfiles += 1
					logging.debug(f'{numfiles} {basename} error: {error}')
				lab.write(labels, gspec.ofolder+basename+gspec.olabelsufx+'.csv')
		if req == 'quit':
			break;

	if gspec.train:
		meansqarederror = int(totalerror / numfiles)
	if gspec.manual or gspec.train:
		mod.write(model, gspec.ofolder+gspec.omodel)

if __name__ == "__main__":
	main()
