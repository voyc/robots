'''
testsk8.py - find donut, crop, find sk8

np.convolve()
cv2.filter2D()

on input both frame and kernel are gray and normalized to -1:+1
onvolved = cv2.filter2D(frame, 1, kernel)
kernel dimensions should be odd, so there is a center

a * b == np.multiply(a,b)  # element-wise multiplication
a @ b == np.matmul(a,b)    # matrix multiplication, 1st row * 1st column, etc
np.dot()                   # dot product
for 2D arrays, np.dot() == np.matmul()

convolution via cv2.filter2D:
	add a frame at half the width/height of the kernel
	element-wise multiplication
	sum 
	normalization to pixel value

applications of convolution: 
	sharpen, blur, emboss
	shrink, expand
	edge detection
	sobel
for example 3x3 filters for these applications,
see https://www.askpython.com/python-modules/opencv-filter2d
'''

import numpy as np
import cv2
import copy
import matplotlib.pyplot as plt
#import scipy
#import scipy.signal
import math
import frame as frm
import label as lbl

idir = '/home/john/media/webapps/sk8mini/awacs/photos/20240312-124118/keep/'
odir = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/'
osuffix = '.labeldonut.txt'

donutkernelfname = '/home/john/media/webapps/sk8mini/awacs/photos/crop/donutfilter.jpg'

sk8kernelfname = '/home/john/media/webapps/sk8mini/awacs/photos/kernels/sk8kernel_%angle%_2.png'
angles = ['C00','L40','L80','R40','R80']
headings = range(0,360,10)

def volver(frame, kernel, verbose=False):
	assert len(frame.shape) == 2, 'frame must have 2 dimensions'
	assert len(kernel.shape) == 2, 'kernel must have 2 dimensions'
	assert frame.dtype == 'float', 'frame values must be dtype float'
	assert kernel.dtype == 'float', 'kernel values must be dtype float'
	assert frame.all() >= 0 and frame.all() <= 255, 'frame values must be 0:255'
	assert kernel.all() >= -1 and frame.all() <= 1, 'kernel must be normalized to -1:+1'
	assert kernel.size % 2 != 0, 'kernel dimensions must both be odd'

	anchor = (np.array(kernel.shape) / 2).astype(np.int8)

	if verbose:
		print('anchor', anchor)
		print('frame')
		print(frame)
		print('kernel')
		print(kernel)
		print('processing')

	output = np.zeros(frame.shape, dtype='float')

	fxmin, fymin = anchor
	fxmax, fymax = frame.shape - anchor
	kxmin, kymin = 0,0
	kxmax, kymax = kernel.shape
	for fx in range(fxmin, fxmax):
		for fy in range(fymin, fymax):
			if verbose:
				print(frame[fx-anchor[0]:fx+anchor[0]+1, fy-anchor[1]:fy+anchor[1]+1])
			output[fx][fy] = np.sum(kernel * frame[fx-anchor[0]:fx+anchor[0]+1, fy-anchor[1]:fy+anchor[1]+1])

	if verbose:
		print('output')
		print(output)
	return output

def histogram(data):
	# use numpy to calculate
	counts, bins = np.histogram(data)

	# use pyplot to draw
	fig, ax = plt.subplots()
	plt.stairs(counts, bins, fill=True)
	fig.canvas.draw()

	# convert pyplot drawing to cv2 image
	img_plot = np.array(fig.canvas.renderer.buffer_rgba())
	img_plot = cv2.cvtColor(img_plot, cv2.COLOR_RGBA2BGR)
	return img_plot

def examine(title, data):
	print('\n'+title)
	print(data.shape, data.dtype)

	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(data)
	print(min_val, max_val, min_loc, max_loc)

	hist = histogram(data)
	cv2.imshow( f'{title} hist', hist)

	# normalize to 0:1 for display as image
	datanorm = (data - min_val) / (max_val - min_val)
	cv2.imshow( f'{title} image', datanorm)
	

# read, rotate, split, and normalize all sk8 kernels into two arrays: b and w
def prepSk8Kernel():
	fqname = sk8kernelfname.replace('%angle%', angles[0])
	dual = cv2.imread(fqname)
	rows, cols, depth = dual.shape

	nheadings = len(headings)
	nangles = len(angles)

	ba = np.zeros((nangles, nheadings, rows, cols), dtype='float')
	wa = np.zeros((nangles, nheadings, rows, cols), dtype='float')

	for iangle in range(nangles):
		angle = angles[iangle]
		fqname = sk8kernelfname.replace('%angle%', angle)
		dual = cv2.imread(fqname)
		for iheading in range(nheadings):
			heading = headings[iheading]
			dualr = rotate(dual, heading)  # rotate
			b,w,_ = cv2.split(dualr)       # split
			#b = ((b / 255) - 0.5) * 2      # normalize to -1:+1
			b = b / 255      		# normalize to 0:1
			#w = ((w / 255) - 0.5) * 2       # normalize to -1:+1
			w = w / 255
			b = b / b.size
			w = w / w.size
			ba[iangle][iheading] = b
			wa[iangle][iheading] = w

	return ba, wa

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

def rotate(image, angle, center=None, scale=1.0):
	# grab the dimensions of the image
	(h, w) = image.shape[:2]

	# if the center is None, initialize it as the center of
	# the image
	if center is None:
	    center = (w // 2, h // 2)

	# perform the rotation
	M = cv2.getRotationMatrix2D(center, angle, scale)
	rotated = cv2.warpAffine(image, M, (w, h))

	# return the rotated image
	return rotated

def convolve(frame, kernel, usevolver=False):
	framef = frame.astype(float)
	if usevolver:
		convolved = volver(framef, kernel)
	else:
		convolved = cv2.filter2D(framef, 1, kernel)
		#convolved = scipy.signal.convolve2d(frame, kernel, mode='same')
	cidx = np.argmax(convolved)
	cy = int(cidx / frame.shape[0])
	cx = cidx % frame.shape[1]
	return cx, cy, convolved 

def convolvesk8(base, ba, wa):
	nangles, nheadings, nrows, ncols = ba.shape

	basei = 255 - base   # invert

	base = base.astype('float')
	cc = np.zeros((ba.shape[0], ba.shape[1], base.shape[0], base.shape[1]), dtype=np.float32)

	for iangle in range(nangles):
		for iheading in range(nheadings):
			continue
			cxw,cyw,convolvedw = convolve(base, wa[iangle][iheading], True)
			cxb,cyb,convolvedb = convolve(basei, ba[iangle][iheading], True)
			cc[iangle][iheading] = convolvedw + convolvedb

	iangle = 0
	iheading = 3
	cxw,cyw,convolvedw = convolve(base, wa[iangle][iheading], True)
	cxb,cyb,convolvedb = convolve(basei, ba[iangle][iheading], True)
	cc[iangle][iheading] = convolvedw + convolvedb
	cidx = np.argmax(cc)
	umax = np.max(cc)
	uangle, uheading, urow, ucol = np.unravel_index(cidx, cc.shape)
	flat = cc.flatten()
	fa = flat[np.isclose(flat, umax)]
	count = (len(fa))
	print(cidx, umax, uangle, uheading, urow, ucol, count)
	examine('0-3', cc[iangle][iheading])

	cc = np.zeros((ba.shape[0], ba.shape[1], base.shape[0], base.shape[1]), dtype=np.float32)
	iangle = 4
	iheading = 18
	cxw,cyw,convolvedw = convolve(base, wa[iangle][iheading], True)
	cxb,cyb,convolvedb = convolve(basei, ba[iangle][iheading], True)
	cc[iangle][iheading] = convolvedw + convolvedb
	cidx = np.argmax(cc)
	umax = np.max(cc)
	uangle, uheading, urow, ucol = np.unravel_index(cidx, cc.shape)
	flat = cc.flatten()
	fa = flat[np.isclose(flat, umax)]
	count = (len(fa))
	print(cidx, umax, uangle, uheading, urow, ucol, count)
	examine('4-18', cc[iangle][iheading])
	cv2.waitKey()

	return ucol, urow, uheading, uangle


def looperdebug(folder, donutkernel, ba, wa):
	labels = []
	fnums = frm.getFrameList(folder)

	bwmask = []
	bbmask = []

	labels = []
	for i in range(len(fnums)):
		if fnums[i] != '00326': continue
		# read the frame
		fqname = frm.fqjoin(idir, fnums[i], 'jpg')
		frame = cv2.imread(fqname)

		# gray and normalize the frame
		framegray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		#framenorm = ((framegray / 255) - 0.5) * 2 # normalize from 0:255 to -1:+1
		framenorm = framegray / 255                # normalize from 0:255 to 0:1

		# find donut center within frame
		cxdonut,cydonut, convolvedonut = convolve(framenorm, donutkernel)

		#cv2.imshow('convolvedonut', convolvedonut)
		#cv2.imshow('framenorm', framenorm)



		# crop frame around donut center
		w = 120
		h = 120
		l = cxdonut - int(w/2)
		r = cxdonut + int(w/2)
		t = cydonut - int(h/2)
		b = cydonut + int(h/2)
		cropgray = framegray[t:b,l:r]
		cropnorm = ((cropgray / 255) - 0.5) * 2 # normalize from 0:255 to -1:+1

		cx,cy,heading,angle = convolvesk8(cropgray, ba, wa)


		cx += l   # uncrop
		cy += t

		label = [2, cx, cy, 59,67,headings[heading],1] # sk8
		labels.append(label)
		print(label)

		cv2.circle( frame, (cxdonut,cydonut), 8, -1)
		cv2.circle( frame, (cx,cy), 8, -1)
		cv2.imshow('frame', frame)
		#cv2.waitKey(0)

	return labels


def main():
	# prep donut kernel
	donutkernel = cv2.imread(donutkernelfname)
	donutkernel = cv2.cvtColor(donutkernel, cv2.COLOR_BGR2GRAY)
	donutkernel = ((donutkernel / 255) - 0.5) * 2 # normalize from 0:255 to -1:+1

	# prep sk8 kernel
	ba, wa = prepSk8Kernel()

	labels = looperdebug(idir, donutkernel, ba, wa)
	print(labels)

if __name__ == '__main__':
	main()
