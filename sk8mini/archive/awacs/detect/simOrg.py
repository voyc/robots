'''
simOrg.py - simulate realtime object detection
'''
import cv2
import numpy as np
import os
import argparse

import detect 
import label as labl
import draw

day_model = [
{
	"cls": 1,
	"name": "cone",
	"algo": 0,
	"rotate": 0,
	"values": [0, 86, 134, 255, 101, 196, 11, 26, 11, 26]
},
{
	"cls": 2,
	"name": "led",
	"algo": 1,
	"rotate": 0,
	"values": [158, 5, 8, 5, 8]
},
{
	"cls": 3,
	"name": "sk8",
	"algo": 0,
	"rotate": 1,
	"values": [31, 56, 48, 114, 22, 177, 35, 69, 59, 92]
}
]
night_model = [
{
	"cls": 1,
	"name": "cone",
	"algo": 0,
	"rotate": 0,
	"values": [0, 69, 108, 156, 77, 148, 14, 40, 15, 40] 
},
{
	"cls": 2,
	"name": "led",
	"algo": 1,
	"rotate": 0,
	"values": [158, 5, 8, 5, 8] 
},
{
	"cls": 3,
	"name": "sk8",
	"algo": 0,
	"rotate": 1,
	"values": [0, 63, 33, 58, 22, 177, 7, 68, 44, 152] 
}
]

gargs = None

def main():
	global gargs
	idir = 'photos/training/'
	idir = 'photos/20231216-092941/'  # day
	idir = 'photos/20240109-174051/'  # night

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'    ,default=idir        ,help='input folder'        )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# loop jpgs
	image_folder = gargs.idir
	jlist = detect.getFrameList(image_folder)
	pause = False
	ndx = 0
	lastframe = len(jlist)-1
	model = None
	while ndx < lastframe:
		# open jpg
		fnum = jlist[ndx]
		fqname = os.path.join(image_folder, fnum + '.jpg')
		img = cv2.imread(fqname, cv2.IMREAD_UNCHANGED)

		# first-time, choose model
		if ndx == 0:
			mean = detect.averageBrightness(img)
			if mean > 110:
				print('using day model')
				model = day_model
			else:
				print('using night model')
				model = night_model

		# detect objectts
		labels = detect.detectObjects(img,model)
		slabels = labl.format(labels, 'realtime')
		print(slabels)

		# display jpg	
		img = draw.drawImage(img,labels, {'format':'sbs'})
		cv2.imshow(f'sim {gargs.idir}', img)

		# animate and allow manual interaction
		key = cv2.waitKey(200)
		if key & 0xFF == ord('q'):	# quit
			break
		elif key & 0xFF == 13:		# return, pause
			pause = not pause
		elif key & 0xFF == ord('n'):	# next
			ndx += 1
			if ndx > lastframe:
				ndx = 0
		elif key & 0xFF == ord('p'):	# prev
			ndx -= 1
			if ndx < 0:
				ndx = lastframe

		if not pause:
			ndx += 1

	cv2.destroyAllWindows()


	#labels = []
	#for m in range(2):
	#	label = detectObjects(img, model, m)
	#	labels += label

	#print(labels)



if __name__ == "__main__":
	main()
