# testalpha.py - test image with alpha channel
# 
# https://en.wikipedia.org/wiki/Alpha_compositing
# https://docs.opencv.org/4.x/d3/df2/tutorial_py_basic_ops.html
# https://stackoverflow.com/questions/40895785/using-opencv-to-overlay-transparent-image-onto-another-image
# 
# make black transparent
# https://www.geeksforgeeks.org/removing-black-background-and-make-transparent-using-python-opencv/

import cv2
import numpy as np
import copy

def overlayTransparent(background, foregrond):
	# make working copies
	composite = copy.deepcopy(background)
	overlay   = copy.deepcopy(foreground)
	
	# both of these images must have an alpha channel
	composite = cv2.cvtColor(composite, cv2.COLOR_BGR2BGRA)
	overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2BGRA)
	
	# in overlay, make black transparent
	tmp = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY) 
	_, alpha = cv2.threshold(tmp,20, 255, cv2.THRESH_BINARY) 
	b, g, r, a = cv2.split(overlay) 
	rgba = [b, g, r, alpha] 
	overlay = cv2.merge(rgba, 4) 
	  
	# normalize alpha channels from 0-255 to 0-1
	alpha_composite = composite[:,:,3] / 255.0
	alpha_overlay = overlay[:,:,3] / 255.0
	
	# calc beta, so that alpha + beta = 1
	beta_composite = 1 - alpha_composite
	beta_overlay = 1 - alpha_overlay
	
	# in composite, set adjusted colors, one pixel at a time
	for color in range(0, 3):
		composite[:,:,color] = \
			alpha_overlay * overlay[:,:,color] + \
			alpha_composite * composite[:,:,color] * beta_overlay
	
	# set adjusted alpha
	composite[:,:,3] = (1 - beta_overlay * beta_composite)
	
	# denormalize back to 0-255
	composite[:,:,3] = composite[:,:,3] * 255
	
	# all images must have same shape for display
	composite = cv2.cvtColor(composite, cv2.COLOR_BGRA2BGR) 
	return composite
	

background_fname = 'photos/20231216-092941/00096.jpg'
foreground_fname = 'photos/20231216-092941/00096.cover.jpg'

background = cv2.imread(background_fname, cv2.IMREAD_UNCHANGED)
foreground = cv2.imread(foreground_fname, cv2.IMREAD_UNCHANGED)

composite = overlayTransparent(background, foreground)

display = np.hstack([background, foreground, composite])
cv2.imshow("background, foreground, composite", display)
cv2.waitKey(0)

