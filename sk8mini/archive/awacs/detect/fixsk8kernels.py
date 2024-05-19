'''
fixsk8kernels.py - combine two sk8 kernels into one file

input: 2 image files, prepared manually in GIMP:
	b for black is the wheels
	w for white is the donut and leds

output: 1 bgr image file, with three layers:
	b inverted 
	w
	empty 

see sk8kernel_master.xcf

vertical guides (width 59)
	29, 30
	8, 51
horizontal guides (height 67)
	33, 34
	13, 54
'''

import numpy as np
import cv2
import argparse

#	%angle%
#	C00 00269.jpg
#	L20 00273.jpg
#	L40 00279.jpg
#	L60 00281.jpg
#	L80 00288.jpg
bfname = '/home/john/media/webapps/sk8mini/awacs/photos/kernels/sk8kernel_%angle%_b.png'
wfname = '/home/john/media/webapps/sk8mini/awacs/photos/kernels/sk8kernel_%angle%_w.png'
ofname = '/home/john/media/webapps/sk8mini/awacs/photos/kernels/sk8kernel_%angle%_2.png'

def examine(grayimage):
	w,h = grayimage.shape
	gray = 0
	black = 0
	white = 0
	other = 0
	total = 0
	a = []
	for x in range(w):
		for y in range(h):
			total += 1
			cg = grayimage[x,y]

			if cg==128:
				gray += 1
			elif cg==0:
				black += 1
			elif cg==255:
				white += 1
			else:
				other += 1
				a.append(cg)
			
	print( grayimage.shape)
	print( sorted(a))
	print( f'gray:{gray}, white:{white}, black:{black}, other:{other}, total:{total}')
	return

def cvtBGR2GRAY(bgrimage, formula='equal'):
	w,h,d = bgrimage.shape
	grayimage = np.zeros((w,h))
	for x in range(w):
		for y in range(h):
			b = bgrimage[x,y][0]
			g = bgrimage[x,y][1]
			r = bgrimage[x,y][2]

			if formula == 'opencv':
				cg = 0.299*r + 0.587*g + 0.114*b
			elif formula == 'equal':
				cg = int(0.333*r + 0.334*g + 0.333*b)

			grayimage[x,y] = cg
	return grayimage


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('angle' ,help='arm angle: C00, L40, L80' )
	args = parser.parse_args()	# returns Namespace object, use dot-notation

	bfqname = bfname.replace('%angle%', args.angle)
	wfqname = wfname.replace('%angle%', args.angle)
	ofqname = ofname.replace('%angle%', args.angle)

	bkernel = cv2.imread(bfqname)
	bgray = cvtBGR2GRAY(bkernel)
	bgray = (255-bgray)

	wkernel = cv2.imread(wfqname)
	wgray = cvtBGR2GRAY(wkernel)

	empty = np.zeros(bgray.shape)

	mgray = cv2.merge((bgray, wgray, empty))
	print(mgray.shape)

	cv2.imshow('mgray', mgray)
	cv2.imshow('bgray', bgray)
	cv2.imshow('wgray', wgray)
	cv2.waitKey()
	examine(bgray)

	cv2.imwrite(ofqname, mgray)	

	if 'L' in ofqname:
		ofqname = ofqname.replace('L', 'R')
		#mgray = cv2.flip(mgray, 1)	
		mgray = cv2.rotate(mgray, cv2.ROTATE_180)	
		cv2.imwrite(ofqname, mgray)	

if __name__ == '__main__':
	main()
