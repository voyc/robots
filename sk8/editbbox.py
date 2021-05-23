''' editbbox.py - bbox editor '''

import os
import cv2 as cv
import numpy as np

dirbase = '/home/john/sk8/bench/train'
dirframe = f'{dirbase}/frame'
dirtrain = f'{dirbase}/train'
fontscale  = 0.6
pxldim = [0,0]

lfarrow = 81
uparrow = 82
dnarrow = 83
rtarrow = 84
pgup = 85
pgdn = 86

class Bbox:
	def __init__(self, cls, lt, wh):
		self.cls = cls
		self.pct_lt = lt
		self.pct_wh = wh

	def toPxl(self,pxldim):
		self.pxl_lt = tuple((np.array(self.pct_lt) * np.array(pxldim)).astype(int))
		self.pxl_wh =  list((np.array(self.pct_wh) * np.array(pxldim)).astype(int))
		self.pxl_rb =  tuple(np.array(self.pxl_lt) + np.array(self.pxl_wh))

	def toPct(self,pxldim):
		self.pct_lt = tuple((np.array(self.pxl_lt) / np.array(pxldim)).astype(float))
		self.pct_wh =  list((np.array(self.pxl_wh) / np.array(pxldim)).astype(float))

	def calc(self):
		self.pxl_wh =  tuple(np.array(self.pxl_rb) - np.array(self.pxl_lt))

	def __str__(self):
		s  = f'pct ltwh: {self.pct_lt}, {self.pct_wh}\n'
		s += f'pxl ltrb: {self.pxl_lt}, {self.pxl_rb}'
		return s

def readBoxes(tname,pxldim):
	fh = open(tname)
	tdata = fh.readlines()
	boxes = []
	for line in tdata:
		a = line.split(' ')
		cls = int(a.pop(0))
		a = list(np.array(a).astype(float)) 
		l,t,w,h = a
		bbox = Bbox(cls, (l,t), [w,h])
		bbox.toPxl(pxldim)
		boxes.append(bbox)
	return boxes
	
def sortcls(e):
	return e.cls 

def rewriteBoxes(boxes,tname):
	boxes.sort(key=sortcls)
	fh = open(tname, 'w')
	for box in boxes:
		box.toPct(pxldim)
		l,t = box.pct_lt
		w,h = box.pct_wh	
		fh.write(f'{box.cls} {l} {t} {w} {h}\n')
	fh.close()

def drawBoxes(boxes,frame,bnum,sledge,fnum):
	img = frame.copy()
	n = 0
	for box in boxes:
		color = (0,0,0)
		if bnum == n:
			color = (255,255,255)
		cv.rectangle(img, box.pxl_lt, box.pxl_rb, color, 1)
		
		w,h = box.pxl_wh
		if w > 20 and h > 20:
			x,y = box.pxl_lt
			y += 20
			cv.putText(img, f'{box.cls}', (x,y), cv.FONT_HERSHEY_SIMPLEX,fontscale,color, 1)

		if bnum == n: 
			l,t = box.pxl_lt
			r,b = box.pxl_rb
			if sledge == 'l':
				pt1 = (l,t)
				pt2 = (l,b)
			elif sledge == 't':
				pt1 = (l,t)
				pt2 = (r,t)
			elif sledge == 'r':
				pt1 = (r,t)
				pt2 = (r,b)
			elif sledge == 'b':
				pt1 = (l,b)
				pt2 = (r,b)

			cv.line(img,pt1,pt2,color,3)
		n += 1
	x = 100
	y = 20
	cv.putText(img, f'frame {fnum}', (x,y), cv.FONT_HERSHEY_SIMPLEX,fontscale,(0,0,0), 1)
	return img

def deleteBox(boxes,bnum):
	del boxes[bnum]

def addBox(boxes):
	box = Bbox(0,(0.3,0.3),(0.5,0.5))
	box.toPxl(pxldim)
	boxes.append(box)

def edgeupleft(boxes,bnum,sledge):
	box = boxes[bnum]
	if sledge == 'l':
		l,t = box.pxl_lt
		if l > 0:
			l -= 1
		boxes[bnum].pxl_lt = (l,t)
	if sledge == 't':
		l,t = box.pxl_lt
		if t > 0:
			t -= 1
		boxes[bnum].pxl_lt = (l,t)
	if sledge == 'r':
		r,b = box.pxl_rb
		if r > 0:
			r -= 1
		boxes[bnum].pxl_rb = (r,b)
	if sledge == 'b':
		r,b = box.pxl_rb
		if b > 0:
			b -= 1
		boxes[bnum].pxl_rb = (r,b)
	box.calc()

def edgedownright(boxes,bnum,sledge):
	box = boxes[bnum]
	if sledge == 'l':
		l,t = box.pxl_lt
		if l < pxldim[0]:
			l += 1
		boxes[bnum].pxl_lt = (l,t)
	if sledge == 't':
		l,t = box.pxl_lt
		if t < pxldim[1]:
			t += 1
		boxes[bnum].pxl_lt = (l,t)
	if sledge == 'r':
		r,b = box.pxl_rb
		if r < pxldim[0]:
			r += 1
		boxes[bnum].pxl_rb = (r,b)
	if sledge == 'b':
		r,b = box.pxl_rb
		if b < pxldim[1]:
			b += 1
		boxes[bnum].pxl_rb = (r,b)

def setcls(boxes,bnum,cls):
	box = boxes[bnum]
	box.cls = cls

# find last framenum
filelist = os.listdir( dirframe)
lastfnum = len(filelist)

# read jpg files in numeric order
fnum = 1
quit = False
while not quit:
	fname = f'{dirframe}/{fnum}.jpg'
	frame = cv.imread( fname, cv.IMREAD_UNCHANGED)
	h,w,d = frame.shape
	pxldim = [w,h]

	tname = f'{dirtrain}/{fnum}.txt'
	boxes = readBoxes(tname,pxldim)

	bnum = 0
	enum = 0
	edgename = ['l','t','r','b']
	sledge = edgename[enum]
	while True:
		img = drawBoxes(boxes,frame,bnum,sledge,fnum)
		wname = 'Frame'
		cv.namedWindow(wname, cv.WINDOW_GUI_EXPANDED)
		cv.imshow(wname, img)
		k = cv.waitKey(0)
		ch = chr(k & 0xFF)
		if ch == 'q':
			quit = True
			break;
		elif ch == 'w':
			rewriteBoxes(boxes,tname)
			print(f'frame {fnum} rewritten')
		elif ch == 'd':
			deleteBox(boxes,bnum)
			bnum -= 1
		elif ch == 'a':
			addBox(boxes)
			bnum = len(boxes)-1
		elif ch == 'n':
			if fnum < lastfnum:
				fnum += 1
				break
		elif ch == 'p':
			if fnum > 1:
				fnum -= 1
				break
		elif ch == '>' or ch == '.':
			if bnum < len(boxes)-1:
				bnum += 1
		elif ch == '<' or ch == ',':
			if bnum > 0:
				bnum -= 1
		elif ch == ' ':
			enum += 1
			if enum > 3:
				enum = 0
			sledge = edgename[enum]
		elif ch >= '0' and ch <= '3':
			setcls(boxes,bnum,int(ch))
		elif k == lfarrow or k == uparrow:
			edgeupleft(boxes,bnum,sledge)
		elif k == rtarrow or k == dnarrow:
			edgedownright(boxes,bnum,sledge)

