' nudge.py - fixup training set of object annotations' 
import os
import cv2
import copy

# one training set and three tests
ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/'
iannosufx = '_annot_extra'
iannosufx = '_annot_short'
iannosufx = '_annot_equal'
iannosufx = '_annot_testr'

c=0
l=1
t=2
w=3
h=4
x=5
y=6
r=7
m=8
e=9

def readAnnotate( fname):
	tlist = []
	with open(fname, 'r') as f:
		a = f.read()
		lines = a.split('\n')
		for line in lines:
			if line == '':
				break;
			row = line.split(', ')
			trow = list(map(int,row))
			tlist.append(trow)
			#print(trow)
	return tlist

def writeAnnotate(annotate, fname):
	with open(fname, 'w') as f:
		for a in annotate:
			f.write( f'{a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]}, {a[5]}, {a[6]}, {a[7]}\n')

def drawAnnotationsOnImage(img,train,ndx):
	# draw the boxes on the original map
	imgMap = img.copy()
	n = 0
	for row in train:
		color = (128,128,255) 
		thickness = 2
		if n == ndx:
			color = (  0,  0,255) 
			thickness = 4
		cls = row[0]
		x = row[1]
		y = row[2]
		w = row[3]
		h = row[4]
		imgMap = cv2.rectangle(imgMap, (x,y), (x+w,y+h), color, thickness) 
		n += 1
	return imgMap

def calcRing(row):
	row[x] = row[l] + int(row[w]/2)
	row[y] = row[t] + int(row[h]/2)
	row[r] = int((row[w] + row[h])/2)

def process(img, train, basename, sufx):
	ndx = 0
	minndx = 0
	maxndx = len(train)-1
	while True:
		imgMap = drawAnnotationsOnImage(img,train,ndx)
		cv2.imshow(basename+sufx, imgMap)
		key = cv2.waitKey(0)
		if key & 0xFF == ord('q'):	# quit
			req = 'quit'
			break
		elif key & 0xFF == 13:		# return, next image
			req = 'next'
			break
		elif key & 0xFF == ord('n'):	# next
			ndx += 1
			if ndx > maxndx:
				ndx = minndx
		elif key & 0xFF == ord('p'):	# previous
			ndx -= 1
			if ndx < minndx:
				ndx = maxndx
		elif key & 0xFF == ord('g'):	# grow
			train[ndx][h] += 1
			train[ndx][w] += 1
		elif key & 0xFF == ord('s'):	# shrink
			train[ndx][h] -= 1
			train[ndx][w] -= 1
		elif key & 0xFF == ord('d'):	# delete
			train.pop(ndx)
		elif key & 0xFF == ord('c'):	# copy/paste, duplicate
			train.insert(ndx, copy.deepcopy(train[ndx]))
			ndx += 1
			train[ndx][l] += 4
			train[ndx][t] += 4
		elif key & 0xFF == ord('w'):	# write, save file
			writeAnnotate(train, ifolder+basename+iannosufx+'.csv')
		elif key & 0xFF == 82 or key & 0xFF == ord('k'):		# up
			train[ndx][t] -= 1
		elif key & 0xFF == 84 or key & 0xFF == ord('j'):		# down
			train[ndx][t] += 1
		elif key & 0xFF == 81 or key & 0xFF == ord('h'):		# left
			train[ndx][l] -= 1
		elif key & 0xFF == 83 or key & 0xFF == ord('l'):		# right
			train[ndx][l] += 1

		calcRing(train[ndx])

	cv2.destroyAllWindows()
	return req # next, quit

def main():
	# loop all images in folder
	for filename in os.listdir(ifolder):
		basename, ext = os.path.splitext(filename)
		if ext == '.jpg': 
			img = cv2.imread(ifolder+filename, cv2.IMREAD_UNCHANGED)
			train = readAnnotate(ifolder+basename+iannosufx+'.csv')
			req = process(img,train,basename, iannosufx)

main()
