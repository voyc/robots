'''
testconvolve.py

convolve(frame, kernel)

because we are using multiplication, and 
multiplying two negaives makes a positive
we cannot allow multiplication of two negatives 
therefore:

frame is usually input as 0 to 255 because its an image
frame is normalized to 0:1
kernel is normalized to -1:+1
the output will be a wide range of positive and negative
sometimes our goal is for the output be a proper image, 0:255
this requires and additional normalization of the output
cv2 imshow can take input of either 0:255 or 0:1, and clips wider ranges

'''

import numpy as np
import cv2
import matplotlib.pyplot as plt
#import scipy
#import scipy.signal

ga = np.array([[1,2,3,4,5],[0,1,2,1,2],[5,4,3,2,1],[4,4,2,0,2],[4,2,1,0,1]], dtype='float')
gb = np.array([[1,0,1],[-1,0,-1],[0,1,0]], dtype='float')

#x = scipy.signal.convolve2d(a,b, mode='same')
#y = cv2.filter2D(p,-1,c)

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

def main():
	volved = volver(ga,gb,False)
	print(volved)
	minval, maxval, minloc, maxloc = cv2.minMaxLoc(volved)
	print(minval, maxval, minloc, maxloc)

	volved_image = (volved - minval) / (maxval - minval)
	cv2.imshow('output', volved_image)
	cv2.waitKey(0)

	# read the frame
	framename = '/home/john/media/webapps/sk8mini/awacs/photos/20240312-124118/keep/00273.jpg'
	frame = cv2.imread(framename)
	frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	#framenorm = ((framegray / 255) - 0.5) * 2 # normalize from 0:255 to -1:+1
	#framenorm = framegray / 255                # normalize from 0:255 to 0:1

	frame = frame[240:360, 240:360]

	kernelname = '/home/john/media/webapps/sk8mini/awacs/photos/kernels/sk8kernel_C00_2.png'
	dual = cv2.imread(kernelname)
	rows, cols, depth = dual.shape

	heading = 180
	dualr = rotate(dual, heading)  # rotate
	b,w,_ = cv2.split(dualr)       # split

	cv2.imshow('frame', frame)
	cv2.imshow('b', b)
	cv2.imshow('w', w)
	cv2.waitKey(0)

	frame = frame.astype('float')

	#b = ((b / 255) - 0.5) * 2      # normalize to -1:+1
	#w = ((w / 255) - 0.5) * 2      # normalize to -1:+1
	b = b / 255      # normalize to 0:1
	w = w / 255      # normalize to 0:1
	#b = b / b.size
	#w = w / w.size

	conw = volver(frame,w,False)
	minval, maxval, minloc, maxloc = cv2.minMaxLoc(conw)
	print(minval, maxval, minloc, maxloc)
	print('count max', len(conw[conw >= maxval]))

	conw_image = (conw - minval) / (maxval - minval)
	minval, maxval, minloc, maxloc = cv2.minMaxLoc(conw_image)
	print(minval, maxval, minloc, maxloc)

	framei = 255 - frame

	conb = volver(framei,b,False)
	minval, maxval, minloc, maxloc = cv2.minMaxLoc(conb)
	print(minval, maxval, minloc, maxloc)
	print('count max', len(conb[conb >= maxval]))

	conb_image = (conb - minval) / (maxval - minval)
	minval, maxval, minloc, maxloc = cv2.minMaxLoc(conb_image)
	print(minval, maxval, minloc, maxloc)

	conc = conb + conw
	minval, maxval, minloc, maxloc = cv2.minMaxLoc(conc)
	conc_image = (conc - minval) / (maxval - minval)

	cv2.imshow('conc', conc_image)
	cv2.imshow('conb', conb_image)
	cv2.imshow('conw', conw_image)
	hist = histogram(conw_image)
	cv2.imshow('hist', hist)
	cv2.waitKey(0)
	




if __name__ == '__main__':
	main()
