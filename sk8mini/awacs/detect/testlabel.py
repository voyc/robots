'''
testlabel.py - unit test the label.py library
'''
import numpy as np
import cv2

import label as labl

def testrrect(hdg):
	# get contour from a test image
	fname = f'photos/test_angles/rect_{hdg}.jpg'
	print(fname)
	img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
	imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	ret, thresh = cv2.threshold(imgray, 127, 255, 0)
	contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnt = contours[0]

	# original rect returned from minAreaRect()
	rect = cv2.minAreaRect(cnt)

	# rect converted to label
	label = labl.labelFromRect(2, rect)
	print(label)

	# optional, examine points and lines in the rect
	box = cv2.boxPoints(rect)
	box = np.intp(box)
	ln01= labl.linelen(box[0], box[1])
	ln03= labl.linelen(box[0], box[3])

def main():
	testrrect('10')  
	testrrect('45')  
	testrrect('80')  
	testrrect('90')  
	testrrect('100') 
	testrrect('135') 
	testrrect('170') 
	testrrect('180')   

	example_label = [
		[1, 533, 517, 20, 20,   0],
		[1, 186, 407, 27, 21, 180],
		[2, 482, 288,  8, 10, 360],
	]
	s = labl.format(example_label)
	print(f'\ndisplay\n{s}')

	s = labl.format(example_label, format='realtime')
	print(f'realtime\n{s}')

	fname = 'temp_test.csv'

	print('\nwrite to file')
	print(example_label)
	labl.write(example_label, fname)

	print('read back in')
	t = labl.read(fname)
	print(t)

if __name__ == '__main__':
	main()

