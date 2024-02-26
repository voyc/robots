'''
testfilter.py - image filtering

'''
import cv2
import numpy as np
from matplotlib import pyplot as plt
import draw

folder = '/home/john/media/webapps/sk8mini/awacs/photos/crop/'
fnameBig = '00139.jpg'
fnameFilter = 'sk8filter.jpg'


def main():
	big = cv2.imread(folder+fnameBig)
	filter = cv2.imread(folder+fnameFilter)

	cx = 380
	cy = 375
	sz = 50
	l = cx-sz
	r = cx+sz
	t = cy-sz
	b = cy+sz
	small = big[t:b, l:r]

	target = big
	
	gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
	hsv = cv2.cvtColor(target, cv2.COLOR_BGR2HSV)

	b,g,r = cv2.split(target)
	h,s,v = cv2.split(hsv)


	#cv2.imshow('b', b)
	#cv2.imshow('g', g)
	#cv2.imshow('r', r)

	#cv2.imshow('h', h)
	#cv2.imshow('s', s)
	#cv2.imshow('v', v)

	#cv2.imshow('big', big)
	#cv2.imshow('filter', filter)
	#cv2.waitKey(0)






	draw.showImage(target, b,g,r,gray, h,s,v, grid=[4,2])

if __name__ == '__main__':
	main()

