''' visualcortex.py - class VisualCortex, edge detection '''

import cv2 as cv
import numpy as np
import universal as uni
import sk8math

class Edge:
	def __init__(self, cls, bbox, inputunits=False):
		self.cls = cls
		self.bbox = bbox

	def __str__(self):
		return f'{self.cls}: {self.bbox}'

class Detect:
	threshhold_defaults = [ 
		# class          hue      sat      val     canny
		( uni.clsCone, 358, 25,  42,100,  35,100,  82,127 ),
		( uni.clsPadl,  52,106,  42,100,  10, 90,  82,127 ),
		( uni.clsPadr, 258,335,  24, 76,  10, 90,  82,127 ),
		( uni.clsSpot, 306,340,  46,100,  10, 90,  82,127 )
	]

	def __init__(self):
		self.img = False
		self.clsfocus = uni.clsSpot
		self.threshholds = self.threshhold_defaults 
		self.images = []

	def __str__(self):
		return str(self.clsfocus)

class VisualCortex:
	use_neural_net = False

	def __init__(self):
		self.detect = Detect()
		self.imgWid = 0
		self.imgHt = 0

	def detectObjects(self,img):
		self.detect.img = img
		if self.use_neural_net:
			pass
		else:
			self.imgHt,self.imgWid,_ = img.shape
			objects = []
			settings = self.detect.threshholds
			for cls in range(len(settings)): 
				self.detectContours(img,settings[cls],objects)
		return objects

	def detectContours(self,img,settings,objects):
		# draw a one-pixel black border around the whole image
		#	When the drone is on the pad, 
		#	each halfpad object extends past the image boundary on three sides, 
		#	and cv.findContours() detects only the remaining edge as an object.
		cv.rectangle(img, (0,0), (self.imgWid-1,self.imgHt-1), (0,0,0), 1)

		# interpolate sk8-trackbar to openCV values for hsv
		sk8_hsv = [1,360,360,100,100,100,100,1,1]
		ocv_hsv = [1,179,179,255,255,255,255,1,1]
		ocv_set = sk8math.interpolate(np.array(settings), 0,np.array(sk8_hsv), 0,np.array(ocv_hsv))
		ocv_set = ocv_set.astype(int)
		cls,hl,hu,sl,su,vl,vu,cl,cu = ocv_set

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

		# take the union of the mask and the original image
		imgMasked = cv.bitwise_and(img,img, mask=imgMask)

		# gaussian blur	
		imgBlur = cv.GaussianBlur(imgMasked, (17, 17), 1)  # started at (7,7);  the bigger kernel size pulls together the pieces of padr
		imgGray = cv.cvtColor(imgBlur, cv.COLOR_BGR2GRAY)
	
		# canny edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
		imgCanny = cv.Canny(imgGray, cl, cu)
	
		# dilate: thicken the line
		kernel = np.ones((5, 5))
		imgDilate = cv.dilate(imgCanny, kernel, iterations=1)

		# get a data array of polygons, one contour boundary for each object
		contours, _ = cv.findContours(imgDilate, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
		if self.detect.clsfocus == cls:
			self.detect.images = [imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate]

		# get bounding box for each contour
		for contour in contours:
			area = cv.contourArea(contour)
			perimeter = cv.arcLength(contour, True)
			polygon = cv.approxPolyDP(contour, 0.02 * perimeter, True)
			l,t,w,h = cv.boundingRect(polygon)

			tl = round(l/self.imgWid, 6)
			tt = round(t/self.imgHt, 6)
			tw = round(w/self.imgWid, 6)
			th = round(h/self.imgHt, 6)

			bbox = sk8math.Bbox(tl,tt,tw,th)
			obj = Edge(cls, bbox)
			objects.append(obj)
		return

	def probeEdgeDetection(self):
		return self.detect

if __name__ == '__main__':
	fname = '/home/john/sk8/bench/testcase/frame/6.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
		quit()

	visualcortex = VisualCortex()
	objs = visualcortex.detectObjects(frame)
	print(*objs, sep='\n')

'''
class VisualCortex
	detectObjects - visual cortex, pareital lobe, occipital lobe, Brodmann area

color coordinate systems
	most systems use RGB: 255,255,255
	openCV by default uses BGR: 255,255,255

trackbar settings are 0 to 360,100,100
opencv values are 0 to 179,255,255

sk8 HSV is defined as 360,100,100
	hue is 0 to 360 degrees on the color wheel
	sat is 0 to 100 percent white
	val is 0 to 100 percent black

openCV HSV is 179,255,255
	255 is the max integer, so the 360 is divided by 2

interpolate
a color coordinate has 3 values
a color threshhold has 6 values (lower-upper or min-max)


todo:
	add trackbars for:
		framenum
		gaus blur kernel size
		gaus blur setting?
'''
