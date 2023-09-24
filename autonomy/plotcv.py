'''
plotcv.py
combine matplotlib and opencv
see https://github.com/voyc/robots/wiki/OpenCV-vs-matplotlib/
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


