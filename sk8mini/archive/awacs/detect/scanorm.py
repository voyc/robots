' scan.py - loop thru images in a folder' 
import os
import glob
import cv2
import argparse

iframepat = '/home/john/media/webapps/sk8mini/awacs/photos/training/{fnum}.jpg'
ilabelpat = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/{fnum}.labeldonut.txt'

def main():
	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-if' ,'--iframepat'        ,default=iframepat  ,help='input frame pattern.'),
	parser.add_argument('-il' ,'--ilabelpat'        ,default=ilabelpat  ,help='input label pattern.'),
	args = parser.parse_args()	# returns Namespace object, use dot-notation

	# loop all images in folder
	pat = args.iframepat.replace('{fnum}', '?????') 
	blist = glob.glob(pat)
	slist = []
	for filename in blist:
		base, ext = os.path.splitext(os.path.basename(filename))
		if ext == '.jpg': 
			slist.append(base)
	blist = sorted(slist)
		
	ndx = 0
	duplist = []
	while ndx in range(len(blist)):
		fnum = blist[ndx]
		fqname = args.iframepat.replace('{fnum}', fnum)
		image = cv2.imread(fqname, cv2.IMREAD_UNCHANGED)
		cv2.putText(image, f'{fnum}', (20,40), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0))

		fqname = args.ilabelpat.replace('{fnum}', fnum)
		print(fqname)
		with open(fqname, 'r') as f:
			label = f.readlines()
		if len(label):
			label = label[0].split(' ')
			[c,x,y,w,h,a,p] = label
			x = float(x)
			y = float(y)
			w = float(w)

			x = int(x * 600)
			y = int(y * 600)
			w = int(w * 600)
			r = int(w/2)
			image = cv2.circle(image, (x,y), r, (0,0,255), 2)
	
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
			duplist.append(fnum)

	cv2.destroyAllWindows()
	print(duplist)

main()
