'''
testsk8.py - find donut, crop, find sk8

np.convolve()
cv2.filter2D()

'''

import numpy as np
import cv2
import copy
import frame as frm
import label as lbl

ikernel = '/home/john/media/webapps/sk8mini/awacs/photos/crop/donutfilter.jpg'
idir = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
idir = '/home/john/media/webapps/sk8mini/awacs/photos/20240312-124118/keep/'
odir = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/'
osuffix = '.labeldonut.txt'

def convolve(frame, kernel):
	convolved = cv2.filter2D(frame, 1, kernel)
	cidx = np.argmax(convolved)
	cx = cidx % 600
	cy = int(cidx / 600)
	return [3, cx, cy, 25, 25, 0, 1] 


def looper(folder, kernel):
	labels = []
	fnums = frm.getFrameList(folder)

	bwmask = []
	bbmask = []

	for i in range(len(fnums)):
		fqname = frm.fqjoin(idir, fnums[i], 'jpg')
		frame = cv2.imread(fqname)
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		norm = ((gray / 255) - 0.5) * 2 # normalize to -1:+1

		# find donut center
		label = convolve(norm, kernel)
		[_, cx, cy, _,_,_,_] = label

		# crop frame around donut center
		# sk8 dim [59,65]
		w = 120
		h = 120
		l = cx - int(w/2)
		r = cx + int(w/2)
		t = cy - int(h/2)
		b = cy + int(h/2)
		x = cx - l
		y = cy - t
		cropped = frame[t:b,l:r]

		graycrop = gray[t:b,l:r]

		t, bmask = cv2.threshold(graycrop, 70, 255, cv2.THRESH_BINARY_INV) 
		t, wmask = cv2.threshold(graycrop, 170, 255, cv2.THRESH_BINARY) 
		canny = cv2.Canny(graycrop, 100, 300) 
		
		if not len(bwmask):
			bwmask = copy.deepcopy(wmask)
			bbmask = copy.deepcopy(bmask)
		else:
			bwmask = bwmask | wmask
			bbmask = bbmask | bmask


		# find deck, wheels, 

		#cv2.imshow('cropped', cropped)
		#cv2.imshow('bmask', bmask)
		#cv2.imshow('wmask', wmask)
		#cv2.waitKey(0)

	return bwmask, bbmask

def main():
	kernel = cv2.imread(ikernel)
	kernel = cv2.cvtColor(kernel, cv2.COLOR_BGR2GRAY)
	kernel = ((kernel / 255) - 0.5) * 2 # normalize to -1:+1

	bwmask, bbmask = looper(idir, kernel)

	cv2.imshow('bwmask', bwmask)
	cv2.imshow('bbmask', bbmask)
	cv2.waitKey(0)

if __name__ == '__main__':
	main()
