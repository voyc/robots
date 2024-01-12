' review.py - draw image with annotations' 
import os
import cv2
import argparse
import math

import draw
import label as lab

gargs = None  # dict containing command-line parameters, initialized in main()
ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/20240109-174051/keep/'
ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/train3/'
ilabelsufx = '_label'

# length of hypotenuse via pythagorean theorem
def linelen(ptA, ptB):
	a = ptB[1] - ptA[1]
	b = ptB[0] - ptA[0]
	hyp = math.sqrt(a**2 + b**2)
	return hyp


def compare (sk8,led):
	reverse = False 
	_,sx,sy,sw,sh,shdg,_ = sk8 
	_,mx,my,mw,mh,_,_ = led

	θ = (shdg-90) * 3.14 / 180.0   # heading in degrees to radians

	x2 = int(sx + (sw/2) * math.cos(θ))
	y2 = int(sy + (sw/2) * math.sin(θ))
	x3 = int(sx - (sw/2) * math.cos(θ))
	y3 = int(sy - (sw/2) * math.sin(θ))

	sA = (x2,y2)
	sB = (x3,y3)
	mctr = (mx,my)

	lenA = linelen(sA,mctr)
	lenB = linelen(sB,mctr)

	if lenA < lenB:
		reverse = True
	return reverse

def fixVehicle(label):
	fixed = []
	sk8 = None
	led = None
	conewd = 22
	coneht = 22
	sk8wd = 51
	sk8ht = 70
	centerimage = (300,300)

	# for cones, set w and h to a constant
	# pick first sk8 and first led
	for row in label:
		cls,x,y,w,h,hdg,scr = row
		if cls == 1:
			w = conewd
			h = coneht 
			fixed.append([cls,x,y,w,h,hdg,scr])
		elif cls == 2:
			if sk8 is None:
				sk8 = row
			else:
				distancesk8 = linelen((sk8[1],sk8[2]),centerimage)
				distancerow = linelen((x,y),centerimage)
				if distancerow < distancesk8:
					sk8 = row
		elif cls == 3 and led is None:
			led = row
		
	if sk8 is not None:
		cls,x,y,w,h,hdg,scr = sk8
		w = sk8wd
		h = sk8ht
		if led is not None:
			reverse = compare(sk8,led)
			if reverse:
				hdg += 180
				if hdg == 360:
					hdg = 0
		fixed.append([cls,x,y,w,h,hdg,scr]) # add fixed sk8
	else:
		fixed.append([2,300,300,sk8wd,sk8ht,0,0]) # add default missing sk8
	return fixed

def countCls(labels, duplist):
	cnts = [0,0,0]
	for row in labels:
		cls = row[0]
		cnts[cls-1] += 1
	return cnts
		
def main():
	global gargs
	# get command-line parameters 

	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=ifolder    ,help='input folder.'),
	parser.add_argument('-of' ,'--ofolder'        ,default=''         ,help='output folder.'),
	parser.add_argument('-is' ,'--ilabelsufx'     ,default=ilabelsufx ,help='input label filename suffix.')
	parser.add_argument('-os' ,'--olabelsufx'     ,default=''         ,help='label filename suffix.')
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation
	if gargs.ofolder == '':
		gargs.ofolder = gargs.ifolder
	if gargs.olabelsufx == '':
		gargs.olabelsufx = gargs.ilabelsufx

	# loop all images in folder
	blist = []
	for filename in os.listdir(gargs.ifolder):
		basename, ext = os.path.splitext(filename)
		if ext == '.jpg': 
			blist.append(basename)
	blist = sorted(blist)
		
	#blist = ['00049', '00062', '00135', '00153', '00187', '00206', '00248', '00258', '00498', '00538', '00644', '00691', '00951', '00958', '00993']

	ndx = 0
	duplist = []
	while ndx in range(len(blist)):
		fname = blist[ndx] + '.jpg'
		image = cv2.imread(os.path.join(gargs.ifolder,fname), cv2.IMREAD_UNCHANGED)
		
		fname = blist[ndx] + gargs.ilabelsufx + '.csv' 
		label = lab.read(os.path.join(gargs.ifolder, fname))

		cnts = countCls(label,duplist)
		print(f'{blist[ndx]}: {cnts}')
		if cnts[2] != 1:
			duplist.append(blist[ndx])

		label = fixVehicle(label)

		annotatedImage = draw.drawImage(image, label)
		cv2.putText(annotatedImage, f'{blist[ndx]}', (20,40), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0))

		cv2.imshow('review', annotatedImage)
		key = cv2.waitKey(0)
		if key & 0xFF == ord('q'):	# quit
			break
		elif key & 0xFF == 13:		# next
			n += 1
		elif key & 0xFF == ord('n'):	# next
			ndx += 1
		elif key & 0xFF == ord('p'):	# previous
			ndx -= 1
		elif key & 0xFF == ord('w'):	# write
			fname = blist[ndx] + gargs.olabelsufx + '.csv' 
			lab.write(label, os.path.join(gargs.ofolder,fname))

	cv2.destroyAllWindows()
	print(duplist)

main()
