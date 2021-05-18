''' eeg.py - class Eeg - probe into internals for human observer '''
import cv2 as cv
import numpy as np
import colorsys
import logging
import universal as uni
from sk8math import *
import hippocampus as hc
import visualcortex as vc
import frontalcortex as fc
import neck as nek

def drawPolygon(img, ptarray, factor=1, color=(255,0,0), linewidth=1):	
	a = np.multiply(ptarray,factor)
	a = a.astype(int)
	for i in range(0,len(a)):
		j = i+1 if i < len(a)-1 else 0
		cv.line(img, tuple(a[i]), tuple(a[j]), color, linewidth)

class Eeg:
	stack_scale     = 0.5
	post_fontscale  = 1.2
	post_lineheight = 35
	post_margin     = 7
	dialog_width    = 480
	dialog_height   = 480
	legit_keypress  = ['n','p','r','s','q']

	def __init__(self, visualcortex=None, hippocampus=None, frontalcortex=None, neck=None):
		self.visualcortex = visualcortex
		self.hippocampus = hippocampus
		self.frontalcortex = frontalcortex
		self.neck = neck
		self.state = 'on' # off or on

		self.cone_radius = 40    # cone diameter is 8 cm
		self.debugPad = True 
		self.pad_radius = 70     # pad is 14 cm square

		self.clsname = [ 'cone','padl','padr','spot' ]
		self.barnames = ( 'cls',  'hue_min', 'hue_max', 'sat_min', 'sat_max', 'val_min', 'val_max', 'canny_lo', 'canny_hi')
		self.barmax           = ( 18, 360,360, 100,100, 100,100, 255,255 )

		self.trackbar_changed = False

	def scan(self):
		print('scan')
		self.detect = self.visualcortex.probeEdgeDetection()
		baseMap, frameMap = self.hippocampus.probeMaps()
		posts = self.hippocampus.probePostData()
		vector = self.frontalcortex.probeVector()
		rccmd = self.neck.probeRcCmd()

		stack = self.drawUI(self.detect.img, frameMap, baseMap, self.detect.images, posts)

		cv.imshow('Image Processing', stack)  # open the image processing window

		self.openSettings()  # open the threshholds trackbar dialog

		k = self.readKeyboard()
		return k

	def openSettings(self):
		print('openSettings')
		# callback on track movement
		def on_trackbar(val):
			threshholds = self.readSettings()
			self.detect.threshholds[self.detect.clsfocus] = threshholds
			self.trackbar_changed = True
			return

		# open the dialog
		name = self.clsname[self.detect.clsfocus]
		cv.namedWindow(name) # default WINDOW_AUTOSIZE, manual resizeable
		cv.resizeWindow( name,self.dialog_width, self.dialog_height)   # ignored with WINDOW_AUTOSIZE

		# create the trackbars
		threshholds = self.detect.threshholds[self.detect.clsfocus]
		for n in range(1,9):
			barname = self.barnames[n]
			value = threshholds[n]
			maxvalue = self.barmax[n]
			cv.createTrackbar(barname, name, value, maxvalue, on_trackbar)

		# create and show the color image for visualizing threshhold hsv values
		imgColor = self.createColorImage(threshholds)
		windowname = self.clsname[self.detect.clsfocus]
		cv.imshow(windowname, imgColor)
	
	def readKeyboard(self):
		print('readKeyboard')
		while True:
			if self.trackbar_changed:
				self.trackbar_changed = False
				ch = 'r'
				break
			k = cv.waitKey(1)  # in milliseconds, must be integer
			ch = chr(k & 0xFF)  # see ord() and chr()
			if ch >= '0' and ch <= '3':
				self.switchClsFocus(int(ch))
				ch = 'r'
				break;
			elif ch in self.legit_keypress:
				break
		return ch

	def switchClsFocus(self, newfocus):
		print('switchClsFocus')
		name = self.clsname[self.detect.clsfocus]
		cv.destroyWindow(name)
		self.detect.clsfocus = newfocus
		
	def drawPosts(self,imgPost,posts):
		linenum = 1
		ssave = ''
		for k in posts.keys():
			v = posts[k]
			s = f'{k}={v}'
			pt = (Eeg.post_margin, Eeg.post_lineheight * linenum)
			cv.putText(imgPost, s, pt, cv.FONT_HERSHEY_SIMPLEX,Eeg.post_fontscale,(0,0,0), 1)
			linenum += 1
			ssave += s + ';'
	
	def readSettings(self):
		print('readSettings')
		# read the threshholds from the trackbars
		threshholds = self.detect.threshholds[self.detect.clsfocus]
		windowname = self.clsname[self.detect.clsfocus]
		#for setting in threshholds:
		#	if setting != 'cls':
		#		threshholds[setting] = cv.getTrackbarPos(setting, name)
		newset = [threshholds[0]]
		for n in range(1,9):
			barname = self.barnames[n]
			value = cv.getTrackbarPos(barname, windowname)
			newset.append(value)
		threshholds = tuple(newset)

		# create the color image for visualizing threshhold hsv values
		imgColor = self.createColorImage(threshholds)

		# show the color image within the dialog window
		cv.imshow(windowname, imgColor)
		self.detect.threshholds[self.detect.clsfocus] = threshholds
		return threshholds

	def createColorImage(self, threshholds):
		print('createColorImage')

		# trackbar threshholds are 360,100,100; convert to 0 to 1
		a = np.array(threshholds) / np.array(self.barmax)
		cls,hl,hu,sl,su,vl,vu,_,_ = a

		# colorsys values are all 0.0 to 1.0
		rl,gl,bl = colorsys.hsv_to_rgb(hl,sl,vl)
		ru,gu,bu = colorsys.hsv_to_rgb(hu,su,vu)

		# RBG and BGR valus are 0 to 255; convert from 0 to 1
		rl,ru,gl,gu,bl,bu = np.array([rl,ru,gl,gu,bl,bu]) * 255
		colormin = bl,gl,rl
		colormax = bu,gu,ru

		# again for hue only
		hrl,hgl,hbl = colorsys.hsv_to_rgb(hl,1.0,1.0)
		hru,hgu,hbu = colorsys.hsv_to_rgb(hu,1.0,1.0)
		hrl,hru,hgl,hgu,hbl,hbu = np.array([hrl,hru,hgl,hgu,hbl,hbu]) * 255
		huemin = hbl,hgl,hrl
		huemax = hbu,hgu,hru

		# an image is an array of numbers, depth 3, opencv uses BGR
		color_image_width = 200
		color_image_height = 100
		imgColor = np.zeros((color_image_height, color_image_width, 3), np.uint8) # blank image

		# divide images into four quadrants, top row is hue range, bottom row is hsv range
		for y in range(0, int(color_image_height/2)):
			for x in range(0, int(color_image_width/2)):
				imgColor[y,x] = huemin
			for x in range(int(color_image_width/2), color_image_width):
				imgColor[y,x] = huemax
		for y in range(int(color_image_height/2), color_image_height):
			for x in range(0, int(color_image_width/2)):
				imgColor[y,x] = colormin
			for x in range(int(color_image_width/2), color_image_width):
				imgColor[y,x] = colormax
		return imgColor
	
	def stackImages(self,scale,imgArray):
		# imgArray is a tuple of lists
		rows = len(imgArray)     # number of lists in the tuple
		cols = len(imgArray[0])  # number of images in the first list

		height,width,depth = imgArray[0][0].shape

		for x in range ( 0, rows):
			for y in range(0, cols):
				# scale images down to fit on screen
				imgArray[x][y] = cv.resize(imgArray[x][y], (0, 0), None, scale, scale)

				# imshow() requires BGR, so convert grayscale images to BGR
				if len(imgArray[x][y].shape) == 2: 
					imgArray[x][y]= cv.cvtColor( imgArray[x][y], cv.COLOR_GRAY2BGR)

		imageBlank = np.zeros((height, width, 3), np.uint8)  # shouldn't this be scaled?
		hor = [imageBlank]*rows  # initialize a blank image space
		for x in range(0, rows):
			hor[x] = np.hstack(imgArray[x])
		ver = np.vstack(hor)

		return ver
	
	def drawMap(self, bmap, img):
		print('drawMap')
		pad = bmap.pad if bmap.pad else False
		spot = bmap.spot if bmap.spot else False
		cones = bmap.cones if bmap.cones else False
		arena = bmap.arena if bmap.arena else False

		# draw arena
		if arena:
			l = int(round(arena.bbox.l * bmap.pxlpermm))
			t = int(round(arena.bbox.t * bmap.pxlpermm))
			r = int(round(arena.bbox.r * bmap.pxlpermm))
			b = int(round(arena.bbox.b * bmap.pxlpermm))
			cv.rectangle(img, (l,t), (r,b), (127,0,0), 1)
	
		# draw cones
		if cones:
			r = int(round(self.cone_radius * bmap.pxlpermm))
			for cone in cones:
				#x = int(round(arena.bbox.center.x + (obj.bbox.center.x * self.frameWidth)))
				#y = int(round(arena.bbox.center.y + (obj.bbox.center.y * self.frameHeight)))
				x = int(round(cone.bbox.center.x * bmap.pxlpermm))
				y = int(round(cone.bbox.center.y * bmap.pxlpermm))
				cv.circle(img,(x,y),r,(0,0,255),1)
	
		# draw pad
		if pad:
			if pad.purpose == 'frame':
				if self.debugPad: # draw the halves
					if pad.padl:
						l = int(round(pad.padl.bbox.l * bmap.pxlpermm))
						t = int(round(pad.padl.bbox.t * bmap.pxlpermm))
						r = int(round(pad.padl.bbox.r * bmap.pxlpermm))
						b = int(round(pad.padl.bbox.b * bmap.pxlpermm))
						cv.rectangle(img, (l,t), (r,b), (0,255,255), 1) # BGR yellow, left

					if pad.padr:
						l = int(round(pad.padr.bbox.l * bmap.pxlpermm))
						t = int(round(pad.padr.bbox.t * bmap.pxlpermm))
						r = int(round(pad.padr.bbox.r * bmap.pxlpermm)) -1
						b = int(round(pad.padr.bbox.b * bmap.pxlpermm)) -1
						cv.rectangle(img, (l,t), (r,b), (255,0,255), 1) # BGR purple, right
				
					if pad.padl and pad.padr:
						drawPolygon(img, [pad.padl.bbox.center.tuple(), pad.padr.bbox.center.tuple(), pad.pt3.tuple()], bmap.pxlpermm)
				
				color = (0,0,0)
				#  outer perimeter
				r = round(self.pad_radius * bmap.pxlpermm)
				x = round(pad.center.x * bmap.pxlpermm)
				y = round(pad.center.y * bmap.pxlpermm)
				cv.circle(img,(x,y),r,color,1)

				# axis with arrow
				pt1, pt2 = calcLine((x,y), r, pad.angle)
				cv.line(img,pt1,pt2,color,1)  # center axis
				cv.circle(img,pt1,3,color,3)   # arrow pointing forward

			elif pad.purpose == 'home':
				# draw props
				r = round(self.pad_radius * bmap.pxlpermm)
				x = round(pad.center.x * bmap.pxlpermm)
				y = round(pad.center.y * bmap.pxlpermm)
				color = (255,128,128)
				radius_prop = .3 * r
				radius_xframe = .7 * r
				pta = []
				for a in [45,135,225,315]:
					ra = np.radians(a)
					xx = x + int(radius_xframe * np.cos(ra))
					xy = y + int(radius_xframe * np.sin(ra))
					pta.append((xx,xy))
					cv.circle(img,(xx,xy),int(radius_prop), color,2)

				# draw x-frame
				cv.line(img,pta[0],pta[2],color,4)  # center axis
				cv.line(img,pta[1],pta[3],color,4)  # center axis
				
				# draw drone body
				#cv.rectangle(img, (l,t), (r,b), (127,0,0), 1)
		if spot:
			color = (255,255,255)
			r = round(spot.bbox.radius * bmap.pxlpermm)
			x = round(spot.bbox.center.x * bmap.pxlpermm)
			y = round(spot.bbox.center.y * bmap.pxlpermm)
			cv.circle(img,(x,y),r,color,1)

	def drawUI(self, img, frameMap, baseMap=False, debugImages=None, posts=None):
		print('drawUI')
		# create empty image for the map
		self.frameHeight,self.frameWidth,self.frameDepth = img.shape
		imgMap = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
		imgMap.fill(255)  # made white
	
		# create final as copy of original
		imgFinal = img.copy()

		# draw maps
		if frameMap:
			self.drawMap(frameMap, imgMap)
			self.drawMap(frameMap, imgFinal)
		if baseMap:
			self.drawMap(baseMap, imgMap)
			self.drawMap(baseMap, imgFinal)

		# draw ovec
		if frameMap and baseMap:
			ptFrame = tuple(np.int0(np.array(self.frameMap.pad.center.tuple()) * bmap.pxlpermm))
			ptBase = tuple(np.int0(np.array(baseMap.pad.center.tuple()) * bmap.pxlpermm))
			color = (0,0,255)
			cv.line(imgMap,ptFrame,ptBase,color,3)  # ovec line between pads
			cv.line(imgFinal,ptFrame,ptBase,color,3)  # ovec line between pads

		# draw internal data calculations posted by programmer
		imgPost = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
		imgPost.fill(255)
		self.drawPosts(imgPost,posts)
	
		# stack all images into one
		#imgTuple = ([imgMap,imgPost,imgFinal],)
		imgTuple = ([imgPost,imgFinal],)
		imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = debugImages
		imgHsv= cv.cvtColor( imgHsv, cv.COLOR_HSV2BGR)
		imgTuple = ([imgPost,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgFinal])
		imgTuple = ([imgPost,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgMap,imgFinal])
		stack = self.stackImages(Eeg.stack_scale,imgTuple)
		return stack

if __name__ == '__main__':
	# wakeup, connect circuits
	visualcortex = vc.VisualCortex()
	hippocampus = hc.Hippocampus()
	hippocampus.start()
	frontalcortex = fc.FrontalCortex()
	neck = nek.Neck()
	eeg = Eeg(visualcortex=visualcortex, hippocampus=hippocampus, frontalcortex=frontalcortex, neck=neck)

	# start sensory-motor circuit

	# eyes receive frame from camera socket

	fname = '/home/john/sk8/bench/testcase/frame/6.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	if frame is None:
		logging.error(f'file not found: {fname}')
		quit()

	# frame sent to visual cortex for edge detection

	objs = visualcortex.detectObjects(frame)
	print(*objs, sep='\n')

	# ears (cerebrum) receive telemetry data from sensors 
	
	# frame and telemetry data are sent to hippocampus for spatial orientation
	mapp = hippocampus.buildMap(objs)	
	hippocampus.stop()
	print(mapp)
	print(*objs, sep='\n')  # objects list has been scrubbed

	# test display of a single frame
	eeg.scan()
	# for more detailed testing of a stream of frames, see sim.py

'''
hsv
see https://alloyui.com/examples/color-picker/hsv.html

h = 6 primary colors, each with a 60 degree range, 6*60=360
    primary     red  yellow  green  cyan  blue  magenta  red
    hue degrees   0      60    120   180   240      300  359  360
    hue inRange   0      30     60    90   120      150  179  180
s = saturation as pct,        0=white, 100=pure color, at zero => gray scale
v = value "intensity" as pct, 0=black, 100=pure color, takes precedence over sat
'''
