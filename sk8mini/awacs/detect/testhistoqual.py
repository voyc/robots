'''
testhistoqual.py - test histogram equalization
and adaptive histogram equalization

https://pyimagesearch.com/2021/02/01/opencv-histogram-equalization-and-adaptive-histogram-equalization-clahe/

normalization - bring the peak to a desired normal value
equalization - limit peaks and valleys
'''

import numpy as np
import cv2
import os
import math
import copy

import draw

# read image
fnamelite = 'photos/training/00118.jpg'
imBGRlite = cv2.imread(fnamelite, cv2.IMREAD_UNCHANGED)
imHSVlite = cv2.cvtColor(imBGRlite, cv2.COLOR_BGR2HSV)
imGRAlite = cv2.cvtColor(imBGRlite, cv2.COLOR_BGR2GRAY)

fnamedark = 'photos/training/00751.jpg'
imBGRdark = cv2.imread(fnamedark, cv2.IMREAD_UNCHANGED)
imHSVdark = cv2.cvtColor(imBGRdark, cv2.COLOR_BGR2HSV)
imGRAdark = cv2.cvtColor(imBGRdark, cv2.COLOR_BGR2GRAY)

# apply linear equation, a normalized version of cv2.convertScaleAbs()
def equalize(im, alpha, betalevel, betafactor):
	eq = copy.deepcopy(im)
	eq = eq / 255 
	eq = eq - .5 
	eq *= alpha
	eq = eq + .5 
	eq *= 255
	beta = betalevel - (np.mean(im) * betafactor)
	eq += beta
	eq = np.clip(eq,0,255)
	eq = eq.astype('uint8')
	return eq

# linear equalization
alpha = 1.0
betafactor = 1
betalevel = 128
imEQlite = equalize(imGRAlite, alpha, betalevel, betafactor)
imEQdark = equalize(imGRAdark, alpha, betalevel, betafactor)

# histogram equalization
imHEQlite = cv2.equalizeHist(imEQlite)
imHEQdark = cv2.equalizeHist(imEQdark)

# adaptive histogram equalization on gray
clipLimit = 2.0
tileGridSize = (8,8)
clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=tileGridSize)
imAGRlite = clahe.apply(imGRAlite)
imAGRdark = clahe.apply(imGRAdark)

# adaptive histogram equalization on eq
imAEQlite = clahe.apply(imEQlite)
imAEQdark = clahe.apply(imEQdark)

image = draw.stack(imGRAlite,imEQlite,imAGRlite,imAEQlite,  imGRAdark,imEQdark,imAGRdark,imAEQdark, grid=[4,2], screen=[1900,900])
cv2.imshow('show', image)
while 1:
	key = cv2.waitKey(0)
	if key == ord('q'):
		break

