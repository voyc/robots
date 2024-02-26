''' 
splitgrid.py - split a grid of images into individual image files
'''
import cv2

def prepData(base, inputfname, gridsize):
	im = cv2.imread(base+inputfname)
	im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
	height, width = im.shape
	
	# cut tiles out of grid file and flatten tile to row
	tiles = []
	for nrow in range(0, int(height/gridsize)):  # rows
		top = nrow * gridsize
		bottom = (nrow+1) * gridsize
		for ncol in range(0, int(width/gridsize)):   # columns
			left = ncol * gridsize
			right = (ncol+1) * gridsize
			tile = im[top:bottom, left:right]

			fname = str(nrow) + 'jdig' + str(ncol) + '.png'
			cv2.imwrite(base + fname, tile)


prepData('photos/jdig/single/', 'jdig-original.png', 28)



