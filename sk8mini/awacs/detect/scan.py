' scan.py - loop thru images in a folder' 
import os
import cv2
import argparse

gargs = None  # dict containing command-line parameters, initialized in main()
ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/20240302-093730/'

def main():
	global gargs

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--ifolder'        ,default=ifolder    ,help='input folder.'),
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	# loop all images in folder
	blist = []
	for filename in os.listdir(gargs.ifolder):
		basename, ext = os.path.splitext(filename)
		if ext == '.jpg': 
			blist.append(basename)
	blist = sorted(blist)
		
	ndx = 0
	duplist = []
	while ndx in range(len(blist)):
		fname = blist[ndx] + '.jpg'
		image = cv2.imread(os.path.join(gargs.ifolder,fname), cv2.IMREAD_UNCHANGED)
		cv2.putText(image, f'{blist[ndx]}', (20,40), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0))
		
		cv2.imshow('review', image)
		key = cv2.waitKey(0)
		if key & 0xFF == ord('q'):	# quit
			break
		elif key & 0xFF == 13:		# next
			n += 1
		elif key & 0xFF == ord('n'):	# next
			ndx += 1
		elif key & 0xFF == ord('p'):	# previous
			ndx -= 1
		elif key & 0xFF == ord('k'):	# keep
			duplist.append(blist[ndx])

	cv2.destroyAllWindows()
	print(duplist)

main()
