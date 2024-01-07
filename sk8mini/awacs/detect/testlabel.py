'''
testlabel.py - test the label.py library
'''

import numpy as np
import cv2

import label

def testrrect(hdg):
	fname = f'/home/john/media/webapps/sk8mini/awacs/photos/training/test_angle_heading/rect_{hdg}.jpg'
	img = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
	imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	ret, thresh = cv2.threshold(imgray, 127, 255, 0)
	contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cnt = contours[0]

	# original rect returned from minAreaRect()
	rect = cv2.minAreaRect(cnt)
	(cx,cy),(w,h),a = rect
	#print(hdg, a, w, h)

	# fudged rrect
	rrect = label.fudgeRect(rect)
	(cx,cy),(w,h),a = rrect
	chdg = label.angle2heading(a)
	print(hdg, a, w, h, chdg)

	# optional, examine points and lines in the rect
	box = cv2.boxPoints(rect)
	box = np.intp(box)
	ln01= label.linelen(box[0], box[1])
	ln03= label.linelen(box[0], box[3])
	return rect




# ------------------- unit test ------------------------- #

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
	s = label.format(example_label)
	print(f'format\n{s}')

	fname = 'test.csv'

	print('write to file')
	print(example_label)
	label.write(example_label, fname)

	print('read back in')
	t = label.read(fname)
	print(t)

if __name__ == '__main__':
	main()

