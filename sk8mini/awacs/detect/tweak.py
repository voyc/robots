'''
tweak.py - tweak the model, while detecting objects in images
'''

import numpy as np
import cv2
from datetime import datetime
import argparse
import logging
import os

import model as mod
import detect
import label as lab
import draw

gargs = None  # dict containing command-line parameters, initialized in main()
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

def readSettings(modcls):
	specs = modcls['spec']
	for spec in specs:
		spec['value'] = cv2.getTrackbarPos(spec['name'], gwindow_name)

#--------------- inner loop per cls ------------------------------------# 

# one image one cls
def processImageCls(fnum, img, model, modcls):
	req = 'next'
	if gargs.manual:
		logging.debug(modcls)
		openSettings(modcls)
		while True:
			readSettings(modcls)
			mod.extractValues(model)
			labels,imgMask = detect.detectObjectsCls(img, modcls)

			# show the images
			imgAnnotated = draw.drawImage(img,labels)
			imgTitle = draw.titleImage(img,fnum)
			stack= np.hstack((imgTitle,imgMask, imgAnnotated))
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
		labels,_ = detect.detectObjectsCls(img, modcls)
	return labels, req

#--------------- outer loop per frame ---------------------------------# 

def main():
	global gargs

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--dir'        ,default=''                            ,help='input folder'                          ),
	parser.add_argument('-im' ,'--model'      ,default='model.json'                  ,help='input model filename'                  ),
	parser.add_argument('-oa' ,'--labelsufx'  ,default='_label'                      ,help='output label filename suffix'          ),
	parser.add_argument('-c'  ,'--cls'        ,default='all'                         ,help='classifier id to processed'            ),
	parser.add_argument('-v'  ,'--verbose'    ,default=False   ,action='store_true'  ,help='display additional output messages'    ),
	parser.add_argument('-q'  ,'--quiet'      ,default=False   ,action='store_true'  ,help='suppresses all output'                 ),
	parser.add_argument('-m'  ,'--manual'     ,default=False   ,action='store_true'  ,help='let user initialize the model manually'),
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	if gargs.cls != 'all':
		gargs.cls = int(gargs.cls)
		print(f"processing cls {gargs.cls}")

	modelfqname = gargs.model
	ch = input(f"model file {modelfqname} will be overwritten. Coninue? (y/n) ")
	if ch != 'y':
		quit()

	labelfilename = os.path.join(gargs.dir, f'?????{gargs.labelsufx}.csv')
	ch = input(f"label files {labelfilename} will be overwritten. Continue? (y/n) ")
	if ch != 'y':
		quit()

	# logging
	logging.basicConfig(format='%(message)s')
	logging.getLogger('').setLevel(logging.INFO)
	if gargs.verbose:
		logging.getLogger('').setLevel(logging.DEBUG)
	if gargs.quiet:
		logging.getLogger('').setLevel(logging.CRITICAL)
	logging.debug(gargs)

	# read model
	model = mod.read(modelfqname)
	logging.info(f'read model {modelfqname}')
	logging.debug(model)

	# loop all images in folder
	jlist = detect.getFrameList(gargs.dir)
	req = 'next'

	ndx = 0
	lastframe = len(jlist)-1
	while ndx <= lastframe:
		fnum = jlist[ndx]
		fqname = os.path.join(gargs.dir,fnum+'.jpg')
		img = cv2.imread(fqname, cv2.IMREAD_UNCHANGED)
		logging.debug(f'reading image from {fqname}')
		logging.debug(f'image shape: {img.shape}')

		# loop classes for in model
		labels = []
		for modcls in model:
			if gargs.cls == 'all' or gargs.cls == modcls['cls']:
				clslabels,req = processImageCls(fnum, img, model, modcls)
				labels += clslabels
				logging.info(f"[{modcls['values']}], # {fnum}, {len(clslabels)}, ")
			if req == 'quit':
				break

		lab.write(labels, os.path.join(gargs.dir, fnum+gargs.labelsufx+'.csv'))
		if req == 'quit':
			break;
		if not gargs.manual and ndx >= lastframe:
			break
		ndx += 1

	mod.write(model, modelfqname)

if __name__ == "__main__":
	main()
