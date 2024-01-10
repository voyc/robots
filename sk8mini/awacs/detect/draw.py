''' 
draw.py - library of drawing functions
'''

import cv2
import numpy as np
import copy

#def draw(img, train, detect):
#	imgMap = img.copy()
#	for trow in train:
#		# draw the training object as green ring, or blue if not matched
#		thickness = 1
#		color = (  0,255,  0) 
#		if trow[m] == 0:
#			color = (255,  0,  0) 
#		x = trow[l]+int(trow[w]/2)
#		y = trow[t]+int(trow[w]/2)
#		r = 10
#		#imgMap = cv2.circle(imgMap, (trow[x],trow[y]), int(trow[r]/2), color, thickness) 
#		imgMap = cv2.circle(imgMap, (x,y), r, color, thickness) 
#
#		# draw the detect object as pink box, or red if extra
#		if trow[m] < len(detect):
#			arow = detect[trow[m]-1]
#		color = (128,128,255) 
#		al = arow[l]
#		at = arow[t]
#		aw = arow[w]
#		ah = arow[h]
#		imgMap = cv2.rectangle(imgMap, (al,at), (al+aw,at+ah), color, thickness) 
#
#		# draw the score of matched and unmatched training objects
#		s = f'{trow[e]}'
#		color = (  0,  0,  0) 
#		cv2.putText(imgMap, s, (x-20,y-20), cv2.FONT_HERSHEY_PLAIN, 1, color)
#
#	# now draw the extras
#	color = (  0,  0,255) 
#	for arow in detect:
#		if arow[m] == 0:
#			al = arow[l]
#			at = arow[t]
#			aw = arow[w]
#			ah = arow[h]
#			imgMap = cv2.rectangle(imgMap, (al,at), (al+aw,at+ah), color, thickness) 
#			s = f'{arow[e]}'
#			color = (  0,  0,  0) 
#			cv2.putText(imgMap, s, (al-20,at), cv2.FONT_HERSHEY_PLAIN, 1, color)
#
#	return imgMap

def createImage(shape=(600,600,3), color=(255,255,255)):
	image = np.zeros(shape, np.uint8)
	image[:,:] = color
	return image

default_options = {
	"color_normal": (128,128,255),    # (B, G, R)
	"color_selected": (  0,  0,255),    # (B, G, R)
	"thickness_normal": 2,
	"thickness_selected": 4,
	"shape": "rectangle"
}

def drawImage(image, label, options=default_options, selected=-1):
	n = 0
	imgOut = copy.deepcopy(image)
	for row in label:
		color = options['color_normal']
		thickness = options['thickness_normal']
		if n == selected:
			color = options['color_selected']
			thickness = options['thickness_selected']
		#cls = row[0]
		#x = row[1]
		#y = row[2]
		#w = row[3]
		#h = row[4]
		cls, x, y, w, h, hdg, scr = row

		if options['shape'] == 'rectangle':
			imgOut = cv2.rectangle(imgOut, (x,y), (x+w,y+h), color, thickness) 
		else:
			cx = x + int(w/2)
			cy = y + int(h/2)
			r = int((row[3]+row[4])/4)
			imgOut = cv2.circle(imgOut, (cx,cy), r, color, thickness) 
		n += 1

	return imgOut

def showImage(img):
	cv2.imshow('show image', img)
	key = cv2.waitKey(0)
	cv2.destroyAllWindows()

def drawLine(img, ctr, angle, length=100):
	x = ctr[0]
	y = ctr[1]
	θ = angle * 3.14 / 180.0
	x2 = int(x + length * math.cos(θ))
	y2 = int(y + length * math.sin(θ))
	x3 = int(x - length * math.cos(θ))
	y3 = int(y - length * math.sin(θ))
	cv2.line(img, (x2,y2), (x3,y3), (0,0,255), 1)

def drawVehicle(img, vehicle):
	box = vehicle[0]	
	ctr = vehicle[1]	
	angle = vehicle[2]	
	cv2.drawContours(img, [box], 0, (0,0,255),1)
	drawLine(img, ctr, angle, 50)

