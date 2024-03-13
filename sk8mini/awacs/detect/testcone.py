'''
testdonut.py - convolve donut pattern in sliding window across image to find center

np.convolve()
cv2.filter2D()

'''

import numpy as np
import cv2
import frame as frm
import label as lbl

ikernel = '/home/john/media/webapps/sk8mini/awacs/photos/crop/conefilter.jpg'
idir = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
odir = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/'
osuffix = '.labelcone.txt'

def convolve(frame, kernel):
	convolved = cv2.filter2D(frame, 1, kernel)
	cidx = np.argmax(convolved)
	cx = cidx % 600
	cy = int(cidx / 600)
	return [1, cx, cy, 21, 21, 0, 1] 


def looper(folder, kernel):
	labels = []
	fnums = frm.getFrameList(folder)
	for i in range(len(fnums)):
		fqname = frm.fqjoin(idir, fnums[i], 'jpg')
		frame = cv2.imread(fqname)
		hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
		h,s,v = cv2.split(hsv)
		frame = ((s / 255) - 0.5) * 2 # normalize to -1:+1
		label = convolve(frame, kernel)
		labels.append(label)

		nlabel = lbl.normalize(label, (600,600))
		s = lbl.toString(nlabel)
		fqout = odir + fnums[i] + osuffix
		with open(fqout, 'w') as f:
			f.write(s)

	return labels	

def main():
	kernel = cv2.imread(ikernel)
	kernel = cv2.cvtColor(kernel, cv2.COLOR_BGR2GRAY)
	kernel = ((kernel / 255) - 0.5) * 2 # normalize to -1:+1
	labels = looper(idir, kernel)

	nlabels = []
	s = ''
	for label in labels:
		nlabel = lbl.normalize(label, (600,600))
		s += lbl.toString(nlabel)
	print(s)

if __name__ == '__main__':
	main()
