''' 
nudge.py - fixup ground-truth set of object annotations

usage:
	python3 nudge.py
		--iimage=/home/john/media/webapps/sk8mini/awacs/photos/training/ 
		--ilabel=/labels/labeldonut.txt 
		--imodel=../0_model
'''
import os
import cv2
import copy
import argparse

import label as lbl
import draw
import frame as frm
import model as mdl

defiimage = '/home/john/media/webapps/sk8mini/awacs/photos/training/*.jpg'
defoimage = '/home/john/media/webapps/sk8mini/awacs/photos/training/*.jpg'
defilabel = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/*.labeldonut.txt'
defolabel = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/*.labeldonut.txt'
defimodel = '/home/john/media/webapps/sk8mini/awacs/photos/training/0_model.json'

gargs = None
gframendx = - 1
gframelist = []
gwritecount = 0
gmodel = []      # read from disk

pgup = 85
pgdn = 86
tab = 8 
shftab = 10

helptext = '''
q quit
n/p next/previous frame
tab/shftab next/prev label
d delete label
c duplicate label
s show label values
h show this help text
w write label, save file
s/g shrink/grow both width and height
,. shrink,grow width
<> shrink,grow height
arrows pan up,down,right,left
pgdn/pgup rotate cw,ccw
'''

def getFnum(increment):
	global gframendx, gframelist
	if gframendx == -1:
		gframelist = frm.getFrameListFromPattern(gargs.iimage)
	gframendx += increment
	if gframendx >= len(gframelist):
		gframendx = 0
	if gframendx < 0:
		gframendx = len(gframelist)-1
	fnum = gframelist[gframendx]
	return fnum

def process(img, labels, fnum):
	global gwritecount
	ndx = 0
	minndx = 0
	while True:
		maxndx = len(labels)-1
		if ndx < minndx:
			ndx = minndx
		if ndx > maxndx:
			ndx = maxndx

		imgMap = draw.annotateImage(img,labels,gmodel,selected=ndx)

		cv2.imshow(fnum, imgMap)
		key = cv2.waitKey(0)
		key &= 0xFF  # I have read that this is redundant.  waitKey already does it.

		breakpoint()
		# quit 
		if key == ord('q'):	# quit
			req = 'quit'
			break

		# navigate frames
		elif key == ord('n'):	# next
			req = 'next'
			break
		elif key == ord('p'):	# previous
			req = 'prev'
			break

		# navigate labels
		elif key == tab:	# next
			ndx += 1
		elif key == shftab:  # previous
			ndx -= 1

		# insert and delete labels 
		elif key == ord('d'):	# delete
			labels.pop(ndx)
		elif key == ord('c'):	# duplicate
			labels.insert(ndx, copy.deepcopy(labels[ndx]))
			ndx += 1
			labels[ndx][lbl.cx] += 4
			labels[ndx][lbl.cy] += 4

		# info
		elif key == ord('s'):	# show label values
			print( labels[ndx] )
		elif key == ord('h'):	# show help
			print(helptext)

		# rewrite label file
		elif key == ord('w'):	# write, save file
			fqname = frm.fqjoin(gargs.odir, fnum, gargs.olabelsufx)
			key = input(f'{fqname} will be written. Continue? (y/n) ')
			if key == 'y':
				lbl.write(labels, fqname)
				gwritecount += 1
				print('done')

		# scale up/down,  grow and shrink
		elif key == ord('f'):	# 1 set standard size for class
			labels[ndx][lbl.w] = 58
			labels[ndx][lbl.h] = 77
			
		elif key == ord('g'):	# grow w,h
			labels[ndx][lbl.h] += 1
			labels[ndx][lbl.w] += 1
		elif key == ord('s'):	# shrink w,h
			labels[ndx][lbl.h] -= 1
			labels[ndx][lbl.w] -= 1

		elif key == ord('.'):	# . grow w
			labels[ndx][lbl.w] += 1
		elif key == ord(','):	# , shrink w
			labels[ndx][lbl.w] -= 1

		elif key == ord('>'):	# > grow h
			labels[ndx][lbl.h] += 1
		elif key == ord('<'):	# < shrink h
			labels[ndx][lbl.h] -= 1

		# pan via arrow keys
		elif key == 82:		# up
			labels[ndx][lbl.cy] -= 1
		elif key == 84:		# down
			labels[ndx][lbl.cy] += 1
		elif key == 81:		# left
			labels[ndx][lbl.cx] -= 1
		elif key == 83:		# right
			labels[ndx][lbl.cx] += 1

		# rotate via pgup/pgdn
		elif key == pgdn:		# pgdn clockwise
			labels[ndx][lbl.hdg] += 1
			if labels[ndx][lbl.hdg] == 360:
				labels[ndx][lbl.hdg] = 0
		elif key == pgup:		# pgup counter-clockwise
			labels[ndx][lbl.hdg] -= 1
			if labels[ndx][lbl.hdg] < 0:
				labels[ndx][lbl.hdg] = 359

	cv2.destroyAllWindows()
	return req # next, quit

def looper():
	# loop thru the list of images
	fnum = getFnum(1)
	while True:
		if fnum is None:
			break;

		# read image and labels
		fname = gargs.iimage.replace("*", fnum)
		img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)

		fname = gargs.ilabel.replace("*", fnum)
		print(fnum)
		print(fname)
		labels = lbl.read(fname)

		# process each image
		req = process(img,labels,fnum)
		if req == 'quit':
			break
		elif req == 'next':
			fnum = getFnum(1)
		elif req == 'prev':
			fnum = getFnum(-1)

	print(f'label updates: {gwritecount}')

def main():
	global gargs, gwritecount, gmodel

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-ii' ,'--iimage'  ,default=defiimage  ,help='input image filename pattern'),
	parser.add_argument('-oi' ,'--oimage'  ,default=defoimage  ,help='output image filename pattern'),
	parser.add_argument('-il' ,'--ilabel'  ,default=defilabel  ,help='input label filename pattern')
	parser.add_argument('-ol' ,'--olabel'  ,default=defolabel  ,help='output label filename pattern')
	parser.add_argument('-im' ,'--imodel'  ,default=defimodel  ,help='input model filename'),
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# show the key usage
	print(helptext)

	# read the model file
	gmodel = mdl.read(gargs.imodel)

	looper()

if __name__ == "__main__":
	main()

