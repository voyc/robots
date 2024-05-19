'''
testsk8.py - find donut, crop, find sk8

going to rotational convolution
kernel enlarged to 79x79
using only wheels
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

sk8kernelfname = '/home/john/media/webapps/sk8mini/awacs/photos/kernels/sk8kernel_%angle%_wheels.png'
angles = ['C00','L40','L80','R40','R80']
headings = range(0,360,20)

kernelsize = np.array([79,79])
kernelcenter = np.array([39,39])
donutoffset = np.array([ # donutoffset = donutcenter - kernelcenter
	[  0, -10],
	[-11,  -8],
	[-15,  -1],
	[ 10,  -8],
	[ 14,  -1]
])
donutcenter = np.array([ # donutcenter = kernelcenter + donutoffset
	[39, 29],
	[28, 31],	
	[24, 38],
	[49, 31],
	[53, 38]
])

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

	awheel = np.zeros((nangles, nheadings, rows, cols), dtype='float')

	for iangle in range(nangles):
		angle = angles[iangle]
		fqname = sk8kernelfname.replace('%angle%', angle)
		wheel = cv2.imread(fqname)
		wheel = cvtBGR2GRAY(wheel)
		wheel = 255 - wheel             # invert
		wheel = wheel / 255      	# normalize to 0:1
		wheel = wheel / wheel.size	# ?
		for iheading in range(nheadings):
			heading = headings[iheading]
			wheel = rotate(wheel, heading)  # rotate
			awheel[iangle][iheading] = wheel

	return awheel

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

def convolvesk8(base, wheels):
	nangles, nheadings, nrows, ncols = wheels.shape

	# input base is cropped to the same size as the kernel
	# input base has been normalized to 0:1, gray-inverted, and float-typed
	assert len(base.shape) == 2, 'base must have 2 dimensions'
	assert base.shape[0] == base.shape[1] == 79, 'base must be 79x79 pixels'
	assert base.dtype == 'float', 'base values must be dtype float'
	assert base.all() >= 0 and base.all() <= 1, 'base values must be 0:1'

	# input wheels is a 2D array of kernels, each rotated by a heading around the donutcenter
	assert wheels.shape == (5, 18, 79, 79), 'wheels array shape must be (5,18,79,79)'

	# calc one score for each rotated kernel
	# a score is the sum of element-wise multiplication of kernel times base
	scores = np.zeros((nangles, nheadings), dtype='float')
	for iangle in range(nangles):
		for iheading in range(nheadings):
			scores[iangle][iheading] = np.sum(base * wheels[iangle][iheading])

	umax = np.max(scores)
	uidx = np.argmax(scores)
	uangle, uheading = np.unravel_index(uidx, scores.shape)

	return uheading, uangle

def centerFromDonut(cxdonut, cydonut, heading,angle):
	x,y = donutoffset[angle]
	return x,y 

def looperdebug(folder, donutkernel, awheel):
	labels = []
	fnums = frm.getFrameList(folder)

	labels = []
	for i in range(len(fnums)):
		# read the frame
		fqname = frm.fqjoin(idir, fnums[i], 'jpg')
		frame = cv2.imread(fqname)

		# gray and normalize the frame
		framegray = cvtBGR2GRAY(frame)
		framenorm = framegray / 255                # normalize from 0:255 to 0:1

		# find donut center within frame
		cxdonut,cydonut, convolvedonut = convolve(framenorm, donutkernel)

		# crop frame around donut center
		w = kernelsize[0]
		h = kernelsize[1]
		l = cxdonut - int(w/2)
		r = cxdonut + math.ceil(w/2)
		t = cydonut - int(h/2)
		b = cydonut + math.ceil(h/2)
		crop = framenorm[t:b,l:r]

		crop = 1 - crop   # invert
		crop = crop.astype('float')

		heading,angle = convolvesk8(crop, awheel)
		print(heading, angle)

		cx,cy = centerFromDonut(cxdonut, cydonut, heading,angle)

		cx += l   # uncrop
		cy += t

		label = [2, cx, cy, 59,67,headings[heading],1] # sk8
		labels.append(label)
		#print(label)

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
	awheel = prepSk8Kernel()

	labels = looperdebug(idir, donutkernel, awheel)
	print(labels)

if __name__ == '__main__':
	main()
