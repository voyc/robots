' crop.py - crop all images in a folder' 
import os
import cv2
import argparse

ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/20240312-124118/keep/'

l = 272
r = 331
t = 267
b = 332

def main():
	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=ifolder    ,help='input folder.'),
	args = parser.parse_args()	# returns Namespace object, use dot-notation

	ocropfolder = os.path.join(args.ifolder, 'crop')

	# loop all images in folder
	blist = []
	for filename in os.listdir(args.ifolder):
		basename, ext = os.path.splitext(filename)
		if ext == '.jpg': 
			blist.append(basename)
	blist = sorted(blist)
		
	ndx = 0
	for ndx in range(len(blist)):
		fname = blist[ndx] + '.jpg'
		fqinputname  = os.path.join(args.ifolder, fname)
		fqoutputname = os.path.join(ocropfolder, fname)

		image = cv2.imread(fqinputname, cv2.IMREAD_UNCHANGED)

		crop = image[t:b, l:r]
		cv2.imwrite(fqoutputname, crop)

main()
