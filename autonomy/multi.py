import multiprocessing as multi
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib import patches
import matplotlib.transforms as mtransforms

fname = '/home/john/webapps/robots/robots/imageprocessing/images/cones/train/helipad_and_3_cones.jpg'

points = [(100,300), (200,100), (300,400)]
center = (200,200)
radius = 200
theta1 = 180.0
theta2 = 270.0
bluecv2 = (255,0,0)     # BGR 0-255
blueplt = (0.0,0.0,1.0) # RGB 0-1

def main():
	p1 = multi.Process(target=withcv2, name="with cv2")
	p1.start()
	p2 = multi.Process(target=withplt, name="with plt")
	p2.start()

def withcv2():
	print('with cv2 started')

	# read image
	cv2src = cv2.imread(fname)   # returns numpy array as BGR
	
	# rectify image
	cv2shape = cv2src.shape  # shape is attribute of the numpy array
	print(f'cv2shape {cv2shape}')

	# draw
	cv2.line(cv2src, points[0], points[1], bluecv2)
	cv2.line(cv2src, points[1], points[2], bluecv2)
	cv2.circle(cv2src, points[0], 8, bluecv2, cv2.FILLED)
	cv2.circle(cv2src, points[1], 8, bluecv2, cv2.FILLED)
	cv2.circle(cv2src, points[2], 8, bluecv2, cv2.FILLED)
	cv2.ellipse(cv2src, center, (int(radius/2), int(radius/2)), -90, theta1, theta2, bluecv2);

	# display image
	cv2.imshow('cv2win',cv2src)
	cv2.setWindowTitle('cv2win', 'with cv2')

	# animation loop
	for i in range(1000000):
		cv2.ellipse(cv2src, center, (i, i), -90, theta1, theta2, bluecv2);
		cv2.imshow('cv2win',cv2src)
		if cv2.waitKey(100) &0xFF == ord('q'): break
	print('with cv2 stopped')

def withplt():
	print('with plt started')

	# read image
	pltsrc = plt.imread(fname)  # returns numpy array as RGB
	
	# rectify image
	fig,ax = plt.subplots()
	pltshape = pltsrc.shape  # shape is attribute of the numpy array
	print(f'pltshape {pltshape}')
	
	im = ax.imshow(pltsrc, interpolation='none', origin='upper') # returns AxesImage
	x1, x2, y1, y2 = im.get_extent()
	print(x1, x2, y1, y2)
	trans = mtransforms.Affine2D().rotate_deg(10).skew_deg(10, 5).scale(1.1, .9).translate(10, 30)

	trans_data = trans + ax.transData
	im.set_transform(trans + ax.transData)
	ax.plot([x1, x2, x2, x1, x1], [y1, y1, y2, y2, y1], "y--", transform=trans_data)

	# draw
	x,y = np.transpose(points)
	plt.plot(x,y, c=blueplt)
	plt.scatter(x,y, color=blueplt)
	ax.add_patch( patches.Arc(center, radius, radius, theta1, theta2, color=blueplt))

	# display image
	fig.canvas.manager.set_window_title('with plt')
	plt.ion()
	plt.show()

	# animation loop
	running = True
	def onpress(event):
		nonlocal running
		if event.key == 'q': running = False
	fig.canvas.mpl_connect('key_press_event', onpress)
	for i in range(1000000):
		ax.add_patch( patches.Arc(center, i, i, theta1, theta2, color=blueplt))
		plt.pause(20/1000)
		if not running: break
	print('with plt stopped')

if __name__ == '__main__':
	main()

