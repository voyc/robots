'''
testunravel.py
'''

import numpy as np
import cv2

def unravel(am, a):
	ax = am
	d = np.array(a.shape)
	ndim = len(d)
	x = np.zeros(ndim)
	i = 0
	while ax > 0:
		print('\nstart', i,ax,x,d)
		sz = a[i].size
		print('sz', sz)
		while (x[i]+1) * sz < ax and ax > 0:
			x[i] += 1
		ax = ax - (x[i]*d[i])
		i += 1
		print('end', i,ax,x,d)

a = np.array([[[1,2,3],[7,8,9],[4,5,6]],[[0.1,0.2,0.3],[0.7,0.8,0.9],[0.4,0.5,0.6]]], dtype='float')
print(a)
m = np.max(a)
am = np.argmax(a)
x,y,z = np.unravel_index(am, a.shape)   # row col
print(m, am, x,y,z)
print(a[x,y,z])
minval, maxval, minloc, maxloc = cv2.minMaxLoc(a[0]) # col row
print(minval, maxval, minloc, maxloc)

x = unravel(am, a)
print(x)
