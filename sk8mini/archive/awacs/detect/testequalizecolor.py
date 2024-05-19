'''
testequalizecolor - test linear equalization of color image

colorspace:
	BGR,RGB
	G GRAY
	HSV  Hue Saturation Value
	LAB  Luminance A(green to magenta)  B(blue to yellow)

gray, value, and luminance appear identical to me

         G
H   S    V
	 L   A   B


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
imLABlite = cv2.cvtColor(imBGRlite, cv2.COLOR_BGR2LAB)

fnamedark = 'photos/training/00751.jpg'
imBGRdark = cv2.imread(fnamedark, cv2.IMREAD_UNCHANGED)
imHSVdark = cv2.cvtColor(imBGRdark, cv2.COLOR_BGR2HSV)
imGRAdark = cv2.cvtColor(imBGRdark, cv2.COLOR_BGR2GRAY)
imLABdark = cv2.cvtColor(imBGRdark, cv2.COLOR_BGR2LAB)

# apply linear equation, a normalized version of cv2.convertScaleAbs()
def equalize(im, alpha, beta):
	eq = copy.deepcopy(im)
	eq = eq / 255 
	eq = eq - .5 
	eq *= alpha
	eq = eq + .5 
	eq *= 255
	eq = np.clip(eq,0,255)
	eq = eq.astype('uint8')
	return eq

# separate hsv channels
hclite,sclite,vclite = cv2.split(imHSVlite)
hm = np.mean(hclite)
sm = np.mean(sclite)
vm = np.mean(vclite)
print(hm,sm,vm)

hcdark,scdark,vcdark = cv2.split(imHSVdark)
hm = np.mean(hcdark)
sm = np.mean(scdark)
vm = np.mean(vcdark)
print(hm,sm,vm)

# separate lab channels
lclite,aclite,bclite = cv2.split(imLABlite)
lcdark,acdark,bcdark = cv2.split(imLABdark)

image = draw.stack( imBGRlite,hclite,sclite,vclite, imBGRlite,lclite,aclite,bclite, imBGRdark,hcdark,scdark,vcdark, imBGRdark,lcdark,acdark,bcdark, grid=[4,4], screen=[1900,900])
cv2.imshow('show', image)
while 1:
	key = cv2.waitKey(0)
	if key == ord('q'):
		break

