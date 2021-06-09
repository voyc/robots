''' visualcortex.py - class VisualCortex, edge detection '''

import cv2 as cv
import numpy as np
import copy
import universal as uni
import sk8mat as sm

#class Edge:
#	def __init__(self, cls, bbox, inputunits=False):
#		self.cls = cls
#		self.bbox = bbox
#
#	def __str__(self):
#		return f'{self.cls}: {self.bbox}'

class Detect:
	# object detection data, saved by VisualCortex, probed and modified by Eeg
	threshhold_seeds = [ 
		#   hue      sat      val     canny    gk  gs,  ok     # class        
		( 358, 13,  42,100,  12,100,  78,127,  17,  1,  11 ),  # uni.clsCone, 
		(  47, 81,  41,100,  10,100,  82,127,  17,  1,   7 ),  # uni.clsPadl, 
		( 296,357,  33,100,  10, 91,  82,127,  17,  1,   7 ),  # uni.clsPadr, 
		( 186,299,  21,100,  12, 97,  82,127,  17,  1,   7 )   # uni.clsSpot, 
	]

	threshhold_seeds_v1 = [ 
		#   hue      sat      val     canny    gk  gs,  ok     # class        
		( 358, 13,  42,100,  12,100,  78,127,  17,  1,   7 ),  # uni.clsCone, 
		(  52,106,  42,100,  10, 90,  82,127,  17,  1,   7 ),  # uni.clsPadl, 
		( 236,330,  24, 76,  10, 50,  82,127,  17,  1,   7 ),  # uni.clsPadr, 
		( 306,340,  50,100,  10, 90,  82,127,  17,  1,   7 )   # uni.clsSpot, 
	]

	threshhold_max = [ 
		#   hue      sat      val     canny    gk  gs,  ok
		[   0,179,  42,100,  35,100,  78,127, 255, 10,   7 ],
		[   0,179,  42,100,  10, 90,  82,127, 255, 10,   7 ],
		[   0,179,  24, 76,  10, 90,  82,127, 255, 10,   7 ],
		[   0,179,  46,100,  10, 90,  82,127, 255, 10,   7 ]
	]

	def __init__(self):
		self.img = False
		self.clsfocus = uni.clsSpot
		self.threshholds = self.threshhold_seeds 
		self.images = []
		self.contours = None

	def __str__(self):
		return str(self.clsfocus)

class VisualCortex:
	use_neural_net = False

	def __init__(self):
		self.detect = Detect() # saved to be probed and modified by eeg
		self.detect.threshholds = Detect.threshhold_seeds
		self.ddim = [0,0]

	def detectObjects(self,img,threshholds):
		self.detect.img = img
		self.detect.threshholds = threshholds
		if self.use_neural_net:
			pass
		else:
			h,w,d = img.shape
			self.ddim = [w,h]
			objects = []
			for cls in range(len(threshholds)): 
				boxes = self.detectContours(img,cls,threshholds[cls])
				objects = objects + boxes	
		#self.filterCones(objects)
		return objects

	#def filterCones(self,objects):
	#	pad = None
	#	cones = []
	#	for obj in objects:
	#		if obj.cls > 0:
	#			if pad:
	#				pad.dbox.unite(obj.dbox)
	#			else:
	#				pad = copy.deepcopy(obj)
	#		else:
	#			cones.append(obj)
	#	for cone in cones:
	#		if pad.dbox.intersects(cone.dbox):
	#			objects.remove(cone)


	def detectContours(self,img,cls,threshholds):
		# draw a one-pixel black border around the whole image
		#	When the drone is on the pad, 
		#	each halfpad object extends past the image boundary on three sides, 
		#	and cv.findContours() detects only the remaining edge as an object.
		def drawBorder(onimg):
			w,h = self.ddim
			cv.rectangle(onimg, (0,0), (w-1,h-1), (0,0,0), 1)

		# interpolate sk8-trackbar to openCV values for hsv (see visualcortex.py notes on hsv)
		sk8_hsv = [360,360,100,100,100,100,1,1,1,1,1]
		ocv_hsv = [179,179,255,255,255,255,1,1,1,1,1]
		ocv_set = sm.interpolate(np.array(threshholds), 0,np.array(sk8_hsv), 0,np.array(ocv_hsv))
		ocv_set = ocv_set.astype(int)
		hl,hu,sl,su,vl,vu,cl,cu,gk,gs,ok = ocv_set

		# prepare a mask of pixels within hsv threshholds
		imgHsv = cv.cvtColor(img,cv.COLOR_BGR2HSV)
		lower = np.array([hl,sl,vl])
		upper = np.array([hu,su,vu])
		imgMask = cv.inRange(imgHsv,lower,upper)
		if hl > hu:  # combine two masks for red-orange plus red-purple
			lower1 = np.array([  0,sl,vl])
			upper1 = np.array([ hu,su,vu])
			lower2 = np.array([ hl,sl,vl])
			upper2 = np.array([179,su,vu])
			mask1 = cv.inRange(imgHsv,lower1,upper1)
			mask2 = cv.inRange(imgHsv,lower2,upper2)
			imgMask = mask1 + mask2

		# murtaza: # mask the original image
		#imgMasked = cv.bitwise_and(img,img, mask=imgMask)
		#imgBlur = cv.GaussianBlur(imgMasked, (gk, gk), gs)  # started at (7,7);  the bigger kernel size pulls together the pieces of padr
		#imgGray = cv.cvtColor(imgBlur, cv.COLOR_BGR2GRAY)

		# remove the small bits of cone; open = erode followed by dilate
		imgMasked = imgMask
		if ok > 0:
			imgMasked = cv.morphologyEx(imgMask, cv.MORPH_OPEN, np.ones((ok, ok)))

		# pull together the pieces of padr
		imgBlur = imgMasked
		if gk+gs > 0:
			imgBlur = cv.GaussianBlur(imgMasked, (gk, gk), gs)
		drawBorder(imgBlur)

		imgGray = imgBlur

		# get a data array of polygons, one contour boundary for each object
		imgCanny = cv.Canny(imgGray, cl, cu)
		imgDilate = cv.dilate(imgCanny, np.ones((5, 5)), iterations=1)
		contours, _ = cv.findContours(imgDilate, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

		# save for drawing by eeg
		if self.detect.clsfocus == cls:
			self.detect.images = [imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate]
			self.detect.contours = copy.deepcopy(contours)

		# take only the largest of padl, padr, and spot objects
		areas = []
		for contour in contours:
			area = cv.contourArea(contour)
			areas.append([area,contour])
		if cls > 0 and len(contours) > 1:
			areas.sort(key=lambda x: x[0], reverse=True)
			contours = [areas[0][1]]

		# get bounding box for each contour
		edges = []
		for contour in contours:
			area = cv.contourArea(contour)
			perimeter = cv.arcLength(contour, True)
			polygon = cv.approxPolyDP(contour, 0.02 * perimeter, True)
			l,t,w,h = cv.boundingRect(polygon)

			edge = sm.Edge(cls)
			edge.dbox = sm.Box((l,t),[w,h])
			edge.fromD(self.ddim)
			edges.append(edge)

		edges.sort(key=lambda x: x.dbox.lt[0])
		return edges

	def probeEdgeDetection(self):
		return self.detect

if __name__ == '__main__':
	fname = '/home/john/sk8/bench/testcase/frame/6.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
		quit()

	visualcortex = VisualCortex()
	objs = visualcortex.detectObjects(frame,Detect.threshhold_seeds)
	print(*objs, sep='\n')

'''
class VisualCortex
	aka: visual cortex, pareital lobe, occipital lobe, Brodmann area
	public function:
		detectObjects()
'''
