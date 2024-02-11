''' 
nudge.py - fixup ground-truth set of object annotations
'''
import os
import cv2
import copy
import argparse

import label as lbl
import draw
import frame as frm
import model as mdl

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
		gframelist = frm.getFrameList(gargs.idir)
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
		img = cv2.imread(frm.fqjoin(gargs.idir, fnum, gargs.iext), cv2.IMREAD_UNCHANGED)
		labels = lbl.read(frm.fqjoin(gargs.idir, fnum, gargs.ilabelsufx))

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

	idir = 'photos/20231216-092941'
	odir = 'photos/20231216-092941'
	iext = 'jpg'
	ilabelsufx = 'truth.csv'
	olabelsufx = 'truth.csv'
	imodel = '0_model'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--idir'        ,default=idir       ,help='input folder'),
	parser.add_argument('-of' ,'--odir'        ,default=''         ,help='output folder'),
	parser.add_argument('-ie' ,'--iext'        ,default=iext       ,help='input image file extension'),
	parser.add_argument('-is' ,'--ilabelsufx'  ,default=ilabelsufx ,help='input label filename suffix')
	parser.add_argument('-os' ,'--olabelsufx'  ,default=''         ,help='output label filename suffix')
	parser.add_argument('-m'  ,'--imodel'      ,default=imodel     ,help='input model file'),
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation
	if gargs.odir == '':
		gargs.odir = gargs.idir
	if gargs.olabelsufx == '':
		gargs.olabelsufx = gargs.ilabelsufx

	gmodel = mdl.read(frm.fqjoin(gargs.idir, gargs.imodel, 'json'))

	print(helptext)
	looper()

if __name__ == "__main__":
	main()

