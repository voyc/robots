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
import frame as frm
import label as lbl

donutkernelfname = '/home/john/media/webapps/sk8mini/awacs/photos/crop/donutfilter.jpg'
sk8kernelfname = '/home/john/media/webapps/sk8mini/awacs/photos/kernels/sk8kernel_0.jpg'
idir = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
idir = '/home/john/media/webapps/sk8mini/awacs/photos/20240312-124118/keep/'
odir = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/'
osuffix = '.labeldonut.txt'

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

def convolve(frame, kernel):
	convolved = cv2.filter2D(frame, 1, kernel)
	cidx = np.argmax(convolved)
	cy = int(cidx / frame.shape[0])
	cx = cidx % frame.shape[1]
	return cx, cy, convolved 

def cvtBGR2GRAY(image):
	w,h,d = image.shape
	gray = 0
	black = 0
	white = 0
	other = 0
	total = 0
	a = []
	for x in range(w):
		for y in range(h):
			total += 1
			b = image[x,y][0]
			g = image[x,y][1]
			r = image[x,y][2]

			#cg = 0.299*r + 0.587*g + 0.114*b
			cg = 0.333*r + 0.333*g + 0.333*b

			if cg==128:
				gray += 1
			elif cg==0:
				black += 1
			elif cg==255:
				white += 1
			else:
				other += 1
				a.append(g)
	a = sorted(a)
	print(a)
	return {'gray':gray, 'white':white, 'black':black, 'other':other, 'total':total}

def countGrays(image):
	w,h = image.shape
	gray = 0
	black = 0
	white = 0
	other = 0
	total = 0
	a = []
	for x in range(w):
		for y in range(h):
			total += 1
			g = image[x,y]
			if g==128:
				gray += 1
			elif g<6:
				black += 1
			elif g==255:
				white += 1
			else:
				other += 1
				a.append(g)
	a = sorted(a)
	print(a)
	return {'gray':gray, 'white':white, 'black':black, 'other':other, 'total':total}

def countColors(image):
	w,h,d = image.shape
	gray = 0
	black = 0
	white = 0
	other = 0
	total = 0
	for x in range(w):
		for y in range(h):
			total += 1
			b = image[x,y][0]
			g = image[x,y][1]
			r = image[x,y][2]
			if b==128 and g==128 and r==128:
				gray += 1
			elif b==0 and g==0 and r==0:
				black += 1
			elif b==255 and g==255 and r==255:
				white += 1
			else:
				other += 1
	return {'gray':gray, 'white':white, 'black':black, 'other':other, 'total':total}


def examine(kernel):
	print(kernel)
	print(kernel.shape)
	gray = cv2.cvtColor(kernel, cv2.COLOR_BGR2GRAY)
	print(kernel.shape)
	plt.hist(gray)
	plt.show()

def looperdebug(folder, donutkernel, sk8kernel):
	labels = []
	fnums = frm.getFrameList(folder)

	bwmask = []
	bbmask = []

	labels = []
	for i in range(len(fnums)):
		# read the frame
		fqname = frm.fqjoin(idir, fnums[i], 'jpg')
		frame = cv2.imread(fqname)

		# gray and normalize the frame
		framegray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		framenorm = ((framegray / 255) - 0.5) * 2 # normalize to -1:+1

		# find donut center within frame
		cxdonut,cydonut, convolvedonut = convolve(framenorm, donutkernel)

		#label = [3, cxdonut, cydonut, 25,25,0,1] # donut
		#labels.append(label)

		# crop frame around donut center
		w = 120
		h = 120
		l = cxdonut - int(w/2)
		r = cxdonut + int(w/2)
		t = cydonut - int(h/2)
		b = cydonut + int(h/2)
		framecrop = frame[t:b,l:r]
		normcrop = framenorm[t:b,l:r]

		# show our work so far
		#cv2.imshow('frame', framecrop)
		#cv2.waitKey(0)
		
		# find sk8 center within cropped
		cx,cy, convolved = convolve(normcrop, sk8kernel)
		cx += l   # uncrop
		cy += t
		#label = [2, cx, cy, 59,65,0,1] # sk8
		#labels.append(label)

		# create a transparent overlay of the kernel

		# position the transparent kernel on top of the frame
		tkernel = sk8kernel
		tkernel = ((tkernel / 2) + 0.5) * 255 #denormalize

		# following line fails with "depth=6"
		#tkernel = cv2.cvtColor(tkernel, cv2.COLOR_GRAY2BGR)
		x = cx - int(sk8kernel.shape[0] /2)
		y = cy - int(sk8kernel.shape[1] /2)
		framegray[y:y+tkernel.shape[0], x:x+tkernel.shape[1]] = tkernel

		#cv2.rectangle(frame, (t,l), (b,r), (255,0,0), 2)
		#cv2.circle(frame, (t,l), 30, (255,0,0), 2)
		#cv2.circle(frame, (cx,cy), 10, (255,0,0), -1)

		# show donut
		rdonut = 12
		cxdonut += 1   # why?  rounding?
		cydonut += 1
		cv2.circle(frame, (cxdonut,cydonut), rdonut, (255,0,0), 2)

		# show crop
		cropradius = 60
		l = cxdonut-cropradius
		r = cxdonut+cropradius
		t = cydonut-cropradius
		b = cydonut+cropradius
		cv2.rectangle(frame, (l,t), (r,b), (255,0,0), 2)

		
		frame = ((convolvedonut / 2) + 0.5) * 255 #denormalize
		#frame = ((convolved / 2) + 0.5) * 255 #denormalize


		# show kernel match position


		cv2.imshow('framegray', framegray)
		cv2.imshow('frame', frame)
		cv2.waitKey(0)

	return labels


def main():
	donutkernel = cv2.imread(donutkernelfname)
	donutkernel = cv2.cvtColor(donutkernel, cv2.COLOR_BGR2GRAY)
	donutkernel = ((donutkernel / 255) - 0.5) * 2 # normalize to -1:+1
	print(f'donut kernel {donutkernel.shape}')

	sk8kernel = cv2.imread(sk8kernelfname)
	a = cvtBGR2GRAY(sk8kernel)
	print(a)
	examine(sk8kernel)
	quit()
	sk8kernel = rotate(sk8kernel, 180)
	sk8kernel = cv2.cvtColor(sk8kernel, cv2.COLOR_BGR2GRAY)
	sk8kernel = ((sk8kernel / 255) - 0.5) * 2 # normalize to -1:+1
	print(f'sk8 kernel {sk8kernel.shape}')

	#labels = looper(idir, donutkernel, sk8kernel)
	labels = looperdebug(idir, donutkernel, sk8kernel)
	print(labels)

if __name__ == '__main__':
	main()
