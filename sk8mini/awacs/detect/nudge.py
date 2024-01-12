' nudge.py - fixup training set of object annotations' 
import os
import cv2
import copy
import argparse

import label as lab
import draw

# one training set and three tests
ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/20240109-174051/keep/'
ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/train3/'
ilabelsufx = '_label'
olabelsufx = '_truth_rbox'

gargs = None
writecount = 0

def process(img, train, basename, sufx):
	global writecount
	ndx = 0
	minndx = 0
	maxndx = len(train)-1
	while True:
		imgMap = draw.drawImage(img,train,selected=ndx)
		cv2.imshow(basename+sufx, imgMap)
		key = cv2.waitKey(0)
		if key & 0xFF == ord('q'):	# quit
			req = 'quit'
			break
		elif key & 0xFF == 13:		# return, next image
			req = 'next'
			break
		elif key & 0xFF == ord('n'):	# next
			ndx += 1
			if ndx > maxndx:
				ndx = minndx
		elif key & 0xFF == ord('p'):	# previous
			ndx -= 1
			if ndx < minndx:
				ndx = maxndx
		elif key & 0xFF == ord('g'):	# grow
			train[ndx][lab.h] += 1
			train[ndx][lab.w] += 1
		elif key & 0xFF == ord('s'):	# shrink
			train[ndx][lab.h] -= 1
			train[ndx][lab.w] -= 1
		elif key & 0xFF == ord('d'):	# delete
			train.pop(ndx)
		elif key & 0xFF == ord('c'):	# copy/paste, duplicate
			train.insert(ndx, copy.deepcopy(train[ndx]))
			ndx += 1
			train[ndx][lab.cx] += 4
			train[ndx][lab.cy] += 4

		elif key & 0xFF == ord('w'):	# write, save file
			lab.write(train, os.path.join(gargs.ofolder, basename+sufx+'.csv'))
			print(f"write {os.path.join(gargs.ofolder, basename+sufx+'.csv')}")
			writecount += 1

		elif key & 0xFF == 82 or key & 0xFF == ord('k'):		# up
			train[ndx][lab.cy] -= 1
		elif key & 0xFF == 84 or key & 0xFF == ord('j'):		# down
			train[ndx][lab.cy] += 1
		elif key & 0xFF == 81 or key & 0xFF == ord('h'):		# left
			train[ndx][lab.cx] -= 1
		elif key & 0xFF == 83 or key & 0xFF == ord('l'):		# right
			train[ndx][lab.cx] += 1

		elif key & 0xFF == ord('>'):		# clockwise
			train[ndx][lab.hdg] += 1
			if train[ndx][lab.hdg] == 360:
				train[ndx][lab.hdg] = 0
		elif key & 0xFF == ord('<'):		# counter-clockwise
			train[ndx][lab.hdg] -= 1
			if train[ndx][lab.hdg] < 0:
				train[ndx][lab.hdg] = 359

	cv2.destroyAllWindows()
	return req # next, quit

def main():
	global gargs, writecount
	# get command-line parameters 

	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=ifolder    ,help='input folder.'),
	parser.add_argument('-of' ,'--ofolder'        ,default=''         ,help='output folder.'),
	parser.add_argument('-is' ,'--ilabelsufx'     ,default=ilabelsufx ,help='input label filename suffix.')
	parser.add_argument('-os' ,'--olabelsufx'     ,default=''         ,help='label filename suffix.')
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation
	if gargs.ofolder == '':
		gargs.ofolder = gargs.ifolder
	if gargs.olabelsufx == '':
		gargs.olabelsufx = gargs.ilabelsufx

	# make a sorted list of all images in folder
	blist = []
	for filename in os.listdir(gargs.ifolder):
		basename, ext = os.path.splitext(filename)
		if ext == '.jpg': 
			blist.append(basename)
	blist = sorted(blist)
		
	# loop thru the list of images
	rownum = 0
	while rownum in range(len(blist)):
		fname = blist[rownum] + '.jpg'
		img = cv2.imread(os.path.join(gargs.ifolder,fname), cv2.IMREAD_UNCHANGED)

		basename = blist[rownum]
		train = lab.read(os.path.join(gargs.ifolder, basename+gargs.ilabelsufx+'.csv'))
		req = process(img,train,basename,gargs.olabelsufx)
		if req == 'quit':
			break
		elif req == 'next':
			rownum += 1
	print(f'labels updated: {writecount}')

main()
