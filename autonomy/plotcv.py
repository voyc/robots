'''
plotcv.py
combine matplotlib and opencv

data format
	both matplotlib and opencv express the image as a numpy array
	you can always manipulate the array directly using matrix math
	or, both matplotlib and opencv provide methods to do sophisticated operations
	there is considerable overlap between the two systems
	you can probably do whatever you want with either system
	and you can mix and match both systems, so long as you know the differences 
	in the way they handle the array
color model
	by default, matplotlib uses RGB, opencv uses BGR
alpha channel
	by default, array shape is (y,x,3)
	can be changed to (y,x,4), for RGBA or BGRA 
	example:
		y,x,d = myarray.shape
		numpy.dstack( ( myarray, numpy.zeros((y, x)) ) )
		https://stackoverflow.com/questions/39642721/adding-alpha-channel-to-rgb-array-using-numpy
display
	by default, matplotlib produces a graph
		with x,y,z axis, with tickmarks and scale
		the graph is positioned with margins inside a resizeable window
	opencv gives a full-size image in a fixed-size window
animation
	both systems provide systems for animation and user-input handling
	matplotlib FuncAnimation allows for an incremental blit 
	matplotlib allows you to change the data of objects already in the plot
	opencv requires you to rewrite the whole screen
user input
	both systems allow you to wait for a key press
	both systems provide an event-handler for keyboard and mouse events
tiling
	numpy hstack() and vstack() can be used to tile multiple images into one
	in addition, matplotlib uses the Figure->Axes->Plot heirarchy of subplots

1. convert plot to image
google: convert matplotlib figure to numpy array opencv
https://www.autoscripts.net/convert-matplotlib-figure-to-cv2-image/

2. overlay transparent plot on top of image
https://docs.opencv.org/3.4/d5/dc4/tutorial_adding_images.html

in cv2,
use cv2.inRange() to make a mask
use cv2.bitwise_and() to make masked image
see ../sk8/visualcortex.py

in matplotlib,
use imshow() twice, where second, top, image has alpha channel
https://stackoverflow.com/questions/49025832/combine-picture-and-plot-with-matplotlib-with-alpha-channel
ax.imshow(bottom, interpolation=None)
ax.imshow(topimg, interpolation=None) # top image must have alpha channel

'''
import numpy as np
import matplotlib.pyplot as plt
import cv2

fname = '/home/john/webapps/robots/robots/imageprocessing/images/cones/train/helipad_and_3_cones.jpg'
src = cv2.imread(fname)
alpha = 0.25  # [0.0-1.0]
beta = (1.0 - alpha)
gamma = 0.0

dimensions = src.shape
height = src.shape[0]
width = src.shape[1] 
number_of_channels = src.shape[2]

# get the size in inches for figsize
dpi = 72.
xinch = width / dpi
yinch = height / dpi
yinch = 720/100
xinch = 540/100


def main():
	fig = plt.figure(figsize=(xinch,yinch))
	fig.patch.set_facecolor('none')
	fig.patch.set_alpha(0.9)


	x1 = np.linspace(0.0, 5.0)
	y1 = np.cos(2 * np.pi * x1) * np.exp(-x1) 
	ax = fig.gca()
	line1, = ax.plot(x1, y1, 'ko-')        # so that we can update data later
	ax.set_facecolor('none')
	#ax.set_alpha(0.5)

	#color = 'black'
	#plt.xlim(0,720)
	#plt.ylim(0,540)
	#plt.autoscale(False)
	#plt.gca().set_aspect('equal', anchor='C')
	#plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	#plt.gca().spines['bottom'].set_color(color)
	#plt.gca().spines['top'].set_color(color)
	#plt.gca().spines['left'].set_color(color)
	#plt.gca().spines['right'].set_color(color)

	#plt.ion()
	#plt.show()
	for i in range(100):
		# update data
		line1.set_ydata(np.cos(2 * np.pi * (x1+i*3.14/2) ) * np.exp(-x1) )
		
		# redraw the canvas
		fig.canvas.draw()
		#plt.pause(.05)

		# convert canvas to image
		s = fig.canvas.tostring_rgb()
		img = np.frombuffer(s, dtype=np.uint8)
		#img  = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
		dim  = fig.canvas.get_width_height()
		dim  = dim[::-1]
		dim  = dim + (3,)
		plotimg  = img.reshape(dim)

		
		# img is rgb, convert to opencv's default bgr
		plotimg = cv2.cvtColor(plotimg,cv2.COLOR_RGB2BGR)
		
		# overlay plot on image
		# src and img must match size and number of channels
		#master = cv2.addWeighted(plotimg, alpha, src, beta, gamma)
		master = cv2.addWeighted(plotimg, .5, src, 1, gamma)

		# display image with opencv or any operation you like
		#cv2.imshow("plot",plotimg)
		#cv2.imshow("src",src)
		cv2.imshow("master",master)
		k = cv2.waitKey(33) & 0xFF
		if k == 27: # escape
			break
		if k == ord('q'):
			break

if __name__ == '__main__':
	main()


