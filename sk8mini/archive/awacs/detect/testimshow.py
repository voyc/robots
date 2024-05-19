import numpy as np
import cv2
from matplotlib import pyplot as plt

'''
testimshow.py

imshow(winname, mat) -> None
. The function may scale the image, depending on its depth:
. - If the image is 8-bit unsigned, it is displayed as is.
. - If the image is 16-bit unsigned or 32-bit integer, the pixels are divided by 256. 
    That is, the value range [0,255\*256] is mapped to [0,255].
. - If the image is 32-bit or 64-bit floating-point, the pixel values are multiplied by 255. That is, the
.   value range [0,1] is mapped to [0,255].

dtype	Range

uint8	0 to 255
uint16	0 to 65535
uint32	0 to (2**32)-1
float	-1 to 1 or 0 to 1
int8	-128 to 127
int16	-32768 to 32767
int32	(-2**31) to (2**31)-1


cv2.convertToShow()

dist = cv2.distanceTransform(src=img,distanceType=cv2.DIST_L2,maskSize=5)
dist1 = cv2.convertScaleAbs(dist)
dist2 = cv2.normalize(dist, None, 255,0, cv2.NORM_MINMAX, cv2.CV_8UC1)

'''

def histogram(data):
	# use numpy to calculate
	counts, bins = np.histogram(data)

	# use pyplot to draw
	fig, ax = plt.subplots()
	plt.stairs(counts, bins, fill=True)
	fig.canvas.draw()

	# convert pyplot drawing to cv2 image
	img_plot = np.array(fig.canvas.renderer.buffer_rgba())
	img_plot = cv2.cvtColor(img_plot, cv2.COLOR_RGBA2BGR)
	return img_plot

data1 = np.array([[70, 20, 52], [70, 64, 25], [52, 90, 35]], dtype='uint8')
print('data1')
print(data1)
print(data1.shape, data1.dtype)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(data1)
print(min_val, max_val, min_loc, max_loc)
hist1 = histogram(data1)
cv2.imshow( 'hist1', hist1)
cv2.imshow( 'data1', data1)

print('\ndatanorm')
datanorm = (data1 - min_val) / (max_val - min_val)
print(datanorm)
print(datanorm.shape, datanorm.dtype)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(datanorm)
print(min_val, max_val, min_loc, max_loc)
histnorm = histogram(datanorm)
cv2.imshow( 'histnorm', histnorm)
cv2.imshow( 'datanorm', datanorm)
cv2.waitKey(0)



#	
#	cv2.imshow( 'data1', data1)
#	
#	data2 = np.array([[1, 0, -1], [0, 0.5, 1], [-1, -0.5, 0]], dtype='float')
#	print(data2.shape, data2.dtype)
#	cv2.imshow( 'data2', data2)
#	
#	# clip the float dist to [0,255] and change the datatype to np.uint8 
#	#dist1 = cv2.convertScaleAbs(dist)
#	
#	#(2) you can also normalize float dist to [0,255] and change datatype by cv2.normalize
#	#cv2.normalize()
#	#dist2 = cv2.normalize(dist, None, 255,0, cv2.NORM_MINMAX, cv2.CV_8UC1)
#	


