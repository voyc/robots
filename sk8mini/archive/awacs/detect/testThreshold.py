'''
testThreshold.py - test various threshold techniques

output is a mask, white on black, white is the foreground object

cv2.threshold is a one-way comparison, either above or below, not a range



'''
import cv2
import numpy as np
import os
import argparse

import detect
import draw



gargs = None

def main():
	global gargs
	iimage = 'photos/20231216-092941/00108.jpg'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-ii' ,'--iimage'    ,default=iimage        ,help='input image'        )
	parser.add_argument('-i' ,'--invert'    ,default=False  ,action='store_true'     ,help='input image'        )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# input image file
	img = cv2.imread(gargs.iimage, cv2.IMREAD_UNCHANGED)
	if img is None:
		print('input image file not found')
		return

	if gargs.invert:
		# looking for black, values below a threshold of gray
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		blur = cv2.GaussianBlur(gray, (7, 7), 0)

		(T, tinv1) = cv2.threshold(blur, 230, 255, cv2.THRESH_BINARY_INV)
		(T, tinv2) = cv2.threshold(blur, 122, 255, cv2.THRESH_BINARY_INV)
		(T, tinv3) = cv2.threshold(blur,  50, 255, cv2.THRESH_BINARY_INV)

		(T, totsu) = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

		amean = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C,     cv2.THRESH_BINARY_INV, 21, 3)
		agaus = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 4)
	else:
		# inverted, looking for white, values above a threshhold of gray
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		blur = cv2.GaussianBlur(gray, (7, 7), 0)

		(T, tinv1) = cv2.threshold(blur, 119, 255, cv2.THRESH_BINARY)
		(T, tinv2) = cv2.threshold(blur, 143, 255, cv2.THRESH_BINARY)
		(T, tinv3) = cv2.threshold(blur, 173, 255, cv2.THRESH_BINARY)

		(T, totsu) = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

		amean = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C,     cv2.THRESH_BINARY, 21, 3)
		agaus = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 4)

	draw.showImage(img, blur, tinv1, tinv2, tinv3, totsu, amean, agaus)

if __name__ == "__main__":
	main()
