'''
keeper.py - manually review photos in a folder and mark some for deletion'
'''

import cv2
import shutil
import os

ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/20240109-174051/'
savefolder = '/home/john/media/webapps/sk8mini/awacs/photos/20240109-174051/keep/'
ext = 'jpg'
minframenum = 1
maxframenum = 1098

framenum = minframenum
while framenum >= minframenum and framenum <= maxframenum:
	fname = f'{framenum:05}.{ext}'
	iname = os.path.join(ifolder, fname)
	savename = os.path.join(savefolder, fname)
	img = cv2.imread(iname, cv2.IMREAD_UNCHANGED)
	print(framenum)
	if img is None:
		framenum += 1
		print('missing image')
		continue

	cv2.imshow('keeper', img)
	key = cv2.waitKey(0)
	if key & 0xFF == ord('q'):	# quit
		break
	elif key & 0xFF == ord('n'):	# next
		framenum += 1
	elif key & 0xFF == ord('p'):	# previous
		framenum -= 1
	elif key & 0xFF == ord('k'):	# keep
		shutil.copy2(iname, savename)
		print(f'copy to {savename}')

cv2.destroyAllWindows()

