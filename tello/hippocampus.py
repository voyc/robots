'''
hippocamapus.py - object detection by color

todo

add home as inverted copy of initial pad
fit arena to rotated rect
superimpose map onto frame
underimpose frame under map
match frame to map

calc pxlpermm from pad, cones, or camera height

'''
import cv2
import numpy as np
from datetime import datetime
import logging

class Hippocampus:
	def __init__(self, ui=True, saveTrain=True):
		self.ui = ui
		self.saveTrain = saveTrain

		# settings
		self.debugCones = False 
		self.debugLzr = False
		self.debugLzl =  False
		self.datalineheight = 22
		self.datalinemargin = 5

		self.save_train_nth = 10
		self.save_post_nth = 60

		self.outfolder = '../imageprocessing/images/cones/new/train/'
		self.cone_radius = 40    # cone diameter is 8 cm
		self.pad_radius = 70     # pad is 14 cm square
		self.arena_padding = 80  # turning radius. keep sk8 in the arena.

		self.arena_margin = 40
		self.barmax = {
			'hue_min'  : 255,
			'hue_max'  : 255,
			'sat_min'  : 255,
			'sat_max'  : 255,
			'val_min'  : 255,
			'val_max'  : 255,
			'canny_lo' : 255,
			'canny_hi' : 255,
			'area_min' : 3000
		}
		self.cone_settings = {
			'hue_min'  : 0,
			'hue_max'  : 8,
			'sat_min'  : 107,
			'sat_max'  : 255,
			'val_min'  : 89,
			'val_max'  : 255,
			'canny_lo' : 82,
			'canny_hi' : 127,  # Canny recommended a upper:lower ratio between 2:1 and 3:1.
			'area_min' : 324,  # min area (size) of contour
		}
		self.padr_settings = {
			'hue_min'  : 130, #122,
			'hue_max'  : 170, #166,
			'sat_min'  : 45,  #37,
			'sat_max'  : 118, #96,
			'val_min'  : 115, #71,
			'val_max'  : 255, #192, #146,
			'canny_lo' : 82,
			'canny_hi' : 127,
			'area_min' : 324,
		}
		self.padl_settings = {
			'hue_min'  : 26,
			'hue_max'  : 53,
			'sat_min'  : 107,
			'sat_max'  : 255,
			'val_min'  : 104,
			'val_max'  : 245,
			'canny_lo' : 82,
			'canny_hi' : 127,
			'area_min' : 324,
		}

		# variables
		self.framenum = 0        # tello    nexus    pixel     
		self.frameWidth  = 0     #     ?      720      720
		self.frameHeight = 0     #     ?      540      405
		self.frameDepth  = 0     #     ?        3        3
		self.camera_height = 0
		self.pxlpermm = 0
		self.imgInt = False
		self.internals = {}
		self.debugImages = []
	
	def openUI(self):
		if self.ui:
			if self.debugCones:
				self.openSettings(self.cone_settings, 'Cone')
			elif self.debugLzr:
				self.openSettings(self.padr_settings, 'LZR')
			elif self.debugLzl:
				self.openSettings(self.padl_settings, 'LZL')

	def closeUI(self):
		if self.ui:
			cv2.destroyAllWindows()

	def post(self,key,value):
		self.internals[key] = value
	
	def drawInternals(self):
		linenum = 1
		ssave = ''
		for k in self.internals.keys():
			v = self.internals[k]
			s = f'{k}={v}'
			pt = (self.datalinemargin, self.datalineheight * linenum)
			cv2.putText(self.imgInt, s, pt, cv2.FONT_HERSHEY_SIMPLEX,.7,(0,0,0), 1)
			linenum += 1
			ssave += s + ';'
		if self.framenum % self.save_post_nth == 0:
			logging.debug(ssave)
	
	def openSettings(self, settings, name):
		def empty(a): # passed to trackbar
			pass
	
		window_name = f'{name} Settings'
		cv2.namedWindow( window_name)
		cv2.resizeWindow( window_name,640,240)
		for setting in settings:
			cv2.createTrackbar(setting, window_name, settings[setting], self.barmax[setting],empty)
	
	def readSettings(self, settings, name):
		window_name = f'{name} Settings'
		for setting in settings:
			settings[setting] = cv2.getTrackbarPos(setting, window_name)
	
	def stackImages(self,scale,imgArray):
		rows = len(imgArray)
		cols = len(imgArray[0])
		rowsAvailable = isinstance(imgArray[0], list)
		width = imgArray[0][0].shape[1]
		height = imgArray[0][0].shape[0]
		if rowsAvailable:
			for x in range ( 0, rows):
				for y in range(0, cols):
					if imgArray[x][y].shape[:2] == imgArray[0][0].shape [:2]:
						imgArray[x][y] = cv2.resize(imgArray[x][y], (0, 0), None, scale, scale)
					else:
						imgArray[x][y] = cv2.resize(imgArray[x][y], (imgArray[0][0].shape[1], imgArray[0][0].shape[0]), None, scale, scale)
					if len(imgArray[x][y].shape) == 2: imgArray[x][y]= cv2.cvtColor( imgArray[x][y], cv2.COLOR_GRAY2BGR)
			imageBlank = np.zeros((height, width, 3), np.uint8)
			hor = [imageBlank]*rows
			hor_con = [imageBlank]*rows
			for x in range(0, rows):
				hor[x] = np.hstack(imgArray[x])
			ver = np.vstack(hor)
		else:
			for x in range(0, rows):
				if imgArray[x].shape[:2] == imgArray[0].shape[:2]:
					imgArray[x] = cv2.resize(imgArray[x], (0, 0), None, scale, scale)
				else:
					imgArray[x] = cv2.resize(imgArray[x], (imgArray[0].shape[1], imgArray[0].shape[0]), None,scale, scale)
				if len(imgArray[x].shape) == 2: imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
			hor= np.hstack(imgArray)
			ver = hor
		return ver
	
	def drawMap(self, arena, cones, pad, img):
		# draw arena
		pl = round(arena['pcx'] + (arena['l'] * self.pxlpermm))
		pt = round(arena['pcy'] + (arena['t'] * self.pxlpermm))
		pr = round(arena['pcx'] + (arena['r'] * self.pxlpermm))
		pb = round(arena['pcy'] + (arena['b'] * self.pxlpermm))
		cv2.rectangle(img, (pl,pt), (pr,pb), (127,0,0), 1)
	
		# draw cones
		r = round(self.cone_radius * self.pxlpermm)
		for cone in cones:
			px = round(arena['pcx'] + (cone[0] * self.pxlpermm))
			py = round(arena['pcy'] + (cone[1] * self.pxlpermm))
			cv2.circle(img,(px,py),r,(0,0,255),1)
	
		# draw pad
		if 'c' in pad:
			r = round(self.pad_radius * self.pxlpermm)
			px = round(arena['pcx'] + (pad['c'][0] * self.pxlpermm))
			py = round(arena['pcy'] + (pad['c'][1] * self.pxlpermm))
			cv2.circle(img,(px,py),r,(255,0,255),1)  # outer perimeter
			pt1, pt2 = self.calcLine((px,py), r, pad['a'])
			cv2.line(img,pt1,pt2,(255,0,255),1)  # center axis
			pt = pt1 if pt1[0] < pt2[0] else pt2 # which end is up?
			cv2.circle(img,pt,3,(255,0,255),1)   # arrow pointing forward
	
	def calcLine(self,c,r,a):
		h = np.radians(a)
		#a = np.tan(a)  # angle in degrees to slope as y/x ratio
		lenc = r
		lenb = round(np.sin(h) * lenc) # opposite
		lena = round(np.cos(h) * lenc) # adjacent
		x = c[0]
		y = c[1]
		x1 = x + lena
		y1 = y + lenb
		x2 = x - lena
		y2 = y - lenb
		return (x1,y1), (x2,y2) 
	
	def drawUI(self, img):
		if self.ui:
			# map
			imgMap = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
			imgMap.fill(255)
			self.drawMap(self.arena, self.cones, self.pad, imgMap)
		
			# frame overlaid with oriented map
			imgFinal = img.copy()
			self.drawMap(self.arena, self.cones, self.pad, imgFinal)

			# internals, values, coefficients, scalars, multipliers, calculations, factors
			# hippocampus internal data calculations
			self.imgInt = np.zeros((self.frameHeight, self.frameWidth, self.frameDepth), np.uint8) # blank image
			self.imgInt.fill(255)
			self.drawInternals()
	
			stack = self.stackImages(0.7,([imgMap,self.imgInt,imgFinal]))
			if self.debugCones or self.debugLzr or self.debugLzl:
				imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate = self.debugImages
				stack = self.stackImages(0.7,([self.imgInt,imgHsv,imgMask,imgMasked,imgBlur],[imgGray,imgCanny,imgDilate,imgMap,imgFinal]))
			cv2.imshow('Image Processing', stack)

	# end UI section, begin image processing section

	def getObjectData(self, cones, padr, padl):
		coneclass = 0
		padrclass  = 1
		padlclass  = 2
		data = []
		for contour in cones:
			obj = self.calcDataFromContour(coneclass, contour)		
			data.append(obj)
	
		for contour in padr:
			obj = self.calcDataFromContour(padrclass, contour)		
			data.append(obj)
			
		for contour in padl:
			obj = self.calcDataFromContour(padlclass, contour)		
			data.append(obj)
		return data
	
	def calcDataFromContour(self, cls, contour):
		# calc area, center, radius in pixels
		area = cv2.contourArea(contour)
		peri = cv2.arcLength(contour, True)
		approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
		x, y, w, h = cv2.boundingRect(approx)
		cx = int(x + (w / 2))
		cy = int(y + (h / 2))
		r = max(w,h)/2  # or r = math.sqrt(a/np.pi())
	
		# rotated rectangle, for pad
		rr = cv2.minAreaRect(contour) # (cx,cy), (w,h), angle
	
		# training data: percentage of image
		tx = round(x/self.frameWidth, 6)
		ty = round(y/self.frameHeight, 6)
		tw = round(w/self.frameWidth, 6)
		th = round(h/self.frameHeight, 6)
	
		obj = {
			'px': x ,  # pixels bounding box
			'py': y ,
			'pw': w ,
			'ph': h ,
			'pr': r ,
			'pcx':cx,
			'pcy':cy,
			'tx':tx,  # training data, pct of frame, bounding box
			'ty':ty,
			'tw':tw,
			'th':th,
			'rr':rr,
			'cl':cls  # class 0:cone, 1:padr, 2:padl
		}
		return obj
	
	def detectObjects(self,img,settings):
		# mask based on hsv ranges
		lower = np.array([settings['hue_min'],settings['sat_min'],settings['val_min']])
		upper = np.array([settings['hue_max'],settings['sat_max'],settings['val_max']])
		imgHsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
		imgMask = cv2.inRange(imgHsv,lower,upper)
		imgMasked = cv2.bitwise_and(img,img, mask=imgMask)
	
		imgBlur = cv2.GaussianBlur(imgMasked, (7, 7), 1)
		imgGray = cv2.cvtColor(imgBlur, cv2.COLOR_BGR2GRAY)
	
		# canny: edge detection.  Canny recommends hi:lo ratio around 2:1 or 3:1.
		imgCanny = cv2.Canny(imgGray, settings['canny_lo'], settings['canny_hi'])
	
		# dilate: thicken the line
		kernel = np.ones((5, 5))
		imgDilate = cv2.dilate(imgCanny, kernel, iterations=1)
	
		# get a data array of polygons, one contour boundary for each object
		contours, _ = cv2.findContours(imgDilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
		self.debugImages = [imgHsv, imgMask, imgMasked, imgBlur, imgGray, imgCanny, imgDilate]
		return contours
	
	def matchMap(data):
		pass
	
	def buildMap(self, data):
		# get average cone diameter in pixels
		diam = []
		for row in data:
			if row['cl'] == 0:
				diam.append(row['ph'])
				diam.append(row['pw'])
		pxlConeWidth = 0
		if len(diam) > 0:
			pxlConeWidth = sum(diam) / len(diam)
		self.post('pxlConeWidth', round(pxlConeWidth))
	
		# calc conversion factor
		mmConeWidth = self.cone_radius * 2
		self.pxlpermm = pxlConeWidth / mmConeWidth
		if self.pxlpermm <= 0:
			self.pxlpermm = 0.1
		self.post('pxlpermm', round(self.pxlpermm,2))
		self.post('camera_height', self.camera_height)
		# pxlpermmat1m = 0.5964285714
		# pxlpermmat2m = 0.3071428571

		# find arena boundary and center in pixels
		pxlarena = {
			'l':self.frameWidth,
			'r':0,
			't':self.frameHeight,
			'b':0,
		}
		for row in data:
			if row['cl'] == 0:
				pcx = row['pcx']
				pcy = row['pcy']
				if pcx < pxlarena['l']:
					pxlarena['l'] = pcx
				if pcx > pxlarena['r']:
					pxlarena['r'] = pcx
				if pcy < pxlarena['t']:
					pxlarena['t'] = pcy
				if pcy > pxlarena['b']:
					pxlarena['b'] = pcy
		a = self.arena_padding * self.pxlpermm
		pxlarena['l'] -= a
		pxlarena['t'] -= a
		pxlarena['r'] += a
		pxlarena['b'] += a
		pxlarena['cx'] = pxlarena['l'] + ((pxlarena['r'] - pxlarena['l']) / 2)
		pxlarena['cy'] = pxlarena['t'] + ((pxlarena['b'] - pxlarena['t']) / 2)
		
		# convert arena boundary and center to mm
		arena = {}
		arena['cx'] = 0  # arena center is null island
		arena['cy'] = 0
		arena['pcx'] = pxlarena['cx']
		arena['pcy'] = pxlarena['cy']
		arena['w'] = (pxlarena['r'] - pxlarena['l']) / self.pxlpermm
		arena['h'] = (pxlarena['b'] - pxlarena['t']) / self.pxlpermm
		arena['r'] = (arena['cx'] + (arena['w'] / 2))
		arena['l'] = (arena['cx'] - (arena['w'] / 2))
		arena['b'] = (arena['cy'] + (arena['h'] / 2))
		arena['t'] = (arena['cy'] - (arena['h'] / 2))
	
		# convert centers to mm
		cones = []
		pad = {}
		for row in data:
			cx = (row['pcx'] - pxlarena['cx']) / self.pxlpermm
			cy = (row['pcy'] - pxlarena['cy']) / self.pxlpermm
			if row['cl'] == 0:
				cones.append((cx,cy))
			elif row['cl'] == 1:
				pad['rc'] = ((cx,cy))
				pad['ra'] = row['rr'][2]
				pad['rrr'] = row['rr']
			elif row['cl'] == 2:
				pad['lc'] = ((cx,cy))
				pad['la'] = row['rr'][2]
				pad['lrr'] = row['rr']
	
		# pad center and angle
		if 'lc' in pad.keys() and 'rc' in pad.keys():
			pad['c'] = self.averageTwoPoints(pad['lc'], pad['rc'])
			pad['a2'] = (pad['la'] + pad['ra']) / 2
			x1,y1 = pad['lc']
			x2,y2 = pad['rc']
			lenx = x2 - x1
			leny = y2 - y1
			oh = leny/lenx if lenx else 0
			angle = np.arctan(oh)
			degrs = np.degrees(angle)
			pad['a'] = degrs - 90 # we want angle to the y-axis instead of to the x-axis
			self.post('pad_angle', round(pad['a']))
			self.post('pad_angle_alt', round(pad['a2']))
		else:
			self.post('cannot see pad', 0)

		self.post('numCones', len(cones))
		return arena, cones, pad
	
	def averageTwoPoints(self, ptr, ptl):
		cxl,cyl = ptl
		cxr,cyr = ptr
		cxc = cxl + ((cxr - cxl) / 2)
		cyc = cyl + ((cyr - cyl) / 2)
		center = (cxc,cyc)
		return center
		
	def saveTrainingData(self,data,img):
		if self.saveTrain and self.framenum % self.save_train_nth == 0:
			fname = f'{self.outfolder}/sk8_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}_ht_{self.camera_height}'
			imgname = f'{fname}.jpg'
			txtname = f'{fname}.txt'
			cv2.imwrite(imgname,img)
			f = open(txtname, 'a')
			for row in data:
				f.write(f"{row['cl']} {row['tx']} {row['ty']} {row['tw']} {row['th']}\n")
			f.close()

	def start(self):
		logging.info('hippocampus starting')
		self.openUI()

	def stop(self):
		logging.info('hippocampus stopping')
		self.closeUI()

	def processFrame(self,img):
		self.framenum += 1
		self.frameHeight,self.frameWidth,self.frameDepth = img.shape
		self.post('image_dim', f'h:{self.frameHeight},w:{self.frameWidth},d:{self.frameDepth}')

		# get settings from trackbars
		if self.ui:
			if self.debugCones:
				self.readSettings( self.cone_settings, 'Cone')
			elif self.debugLzr:
				self.readSettings( self.padr_settings, 'LZR')
			elif self.debugLzl:
				self.readSettings( self.padl_settings, 'LZL')

		# find contors
		conecontours = self.detectObjects(img, self.cone_settings)
		padrcontours = self.detectObjects(img, self.padr_settings)
		padlcontours = self.detectObjects(img, self.padl_settings)
	
		# reduce the contours to pixel data
		data = self.getObjectData(conecontours, padrcontours, padlcontours)

		# convert pixel data to map coordinates
		self.arena, self.cones, self.pad = self.buildMap(data)
		
		# orient frame to map

		# save data for mission debriefing and neural net training
		self.saveTrainingData(data, img)

	def parseFilenameForHeight(self, fname):
		height = int(fname.split('_ht_')[1].split('.')[0])
		return height

if __name__ == '__main__':
	def startLogging(filename='drone.log'):
		logging.basicConfig(
			format='%(asctime)s %(levelname)s %(message)s', 
			filename=filename, 
			level=logging.DEBUG) # 10 debug, 20 info, 30 warning, 40 error, 50 critical
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)
		logging.getLogger('').addHandler(console)
		logging.info('starting')

	startLogging()

	imgfolder = '../imageprocessing/images/cones/train/'
	imgfile = 'helipad_and_3_cones.jpg'
	imgfile = 'IMG_20200623_174503.jpg'
	imgfile = 'sk8_2_meter_ht_2000.jpg'
	imgfile = 'sk8_1_meter_ht_1000.jpg'

	hippocampus = Hippocampus(True, True)
	hippocampus.start()

	while True:
		img = cv2.imread(imgfolder+imgfile, cv2.IMREAD_UNCHANGED)
		hippocampus.camera_height = hippocampus.parseFilenameForHeight(imgfolder+imgfile)

		hippocampus.processFrame(img)
		
		hippocampus.drawUI(img)

		if cv2.waitKey(1) & 0xFF == ord('q'):
			break

	hippocampus.stop()

