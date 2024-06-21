'''
testlayout.py

box model (CSS terminology):
	CSS		mpl
	content		data, defined by extent or xlim/ylim
	padding		"margin", increase with plt.margins(sz)
	border		"spines", four of them
	-		ticks
	-		tick labels
	margin		(unnamed), but plt.tight_layout() removes it

coordinate system, data extent:
	by default the extent is normalized to 0:1 with origin in lower-left

	you can specify the extent explicitly 
		fig, ax = plt.subplots()
		plt.xlim(-132,+132)  # change extent and origin
		plt.ylim(-132,+132)

	an image by default has an extent
		equal to the pixel dimensions of the image
		with the origin in the upper-left

	you can specify the image's extent explicitly on imshow()
		plt.imshow(image, extent=[-132,132,-132,132]) 

to save an image file, use fig.savefig(fname)
	the coordinate system is changed to pixels, with origin at upper-left 
	number of pixels can be set by size and dpi
	by default, border, ticks, and margin are added

subplot vs axes
	ax = fig.add_subplot(111)  # has ticks, labels, and irremoveable margins
	ax = fig.add_axes((0,0,1,1)  # none of that
'''

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import specs


fname_aerial = 'photos/20240618-193901/1718714360_61.jpg'
fname_mapped = 'photos/20240618-193901/1718714360_78.png'
fname_localtemp = 'testdraw.png'

def createImageAxes():
	fig = plt.figure()
	ax = fig.add_axes((0,0,1,1))  # axes good
	plt.xlim(-132,+132)
	plt.ylim(-132,+132)

	fig.savefig(fname_localtemp)
	return fig

def createImageSubplot():
	fig = plt.figure()
	ax = fig.add_subplot(111)   # ticks, labels, margins

	plt.xlim(-132,+132)
	plt.ylim(-132,+132)
	stripBorder(fig,ax)

	fig.savefig(fname_localtemp)
	return fig

def draw(ax):
	# draw three circles
	circ = plt.Circle([132,132], 10, color='y')
	ax.add_artist(circ)

	circ = plt.Circle([0,0], 10, color='b')
	ax.add_artist(circ)

	circ = plt.Circle([-132,-132], 10, color='g')
	ax.add_artist(circ)

def stripBorder(fig,ax):
	ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize
	fig.set_size_inches(6,6)  # savefig with dpi=132, for a 600x600 image to match aerial

	# remove borders, ticks, margins
	#plt.tight_layout()
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False) 
	plt.tick_params(axis='y', which='both', right=False, left=False, labelleft=False) 
	#for pos in ['right', 'top', 'bottom', 'left']: plt.gca().spines[pos].set_visible(False) 

       	# All dimensions are fraction of the figure width or height.
	mpl.rcParams['figure.subplot.left'] = 0.001 # the left side of the subplots of the figure
	mpl.rcParams['figure.subplot.right'] = 0.999 # the right side of the subplots of the figure
	mpl.rcParams['figure.subplot.bottom'] = 0.001 # the bottom of the subplots of the figure
	mpl.rcParams['figure.subplot.top'] = 0.999
	mpl.rcParams['figure.subplot.wspace'] = 0.001 # the amount of width reserved for blank space between subplots
	mpl.rcParams['figure.subplot.hspace'] = 0.001 # the amount of height reserved for white space between subplots


	mpl.rcParams['axes.xmargin'] = 0.001
	mpl.rcParams['axes.ymargin'] = 0.001
	mpl.rcParams['axes.zmargin'] = 0.001

	mpl.rcParams['savefig.dpi'] = 100
	mpl.rcParams['savefig.pad_inches'] = 0.0
	mpl.rcParams['savefig.transparent'] = True
	mpl.rcParams['savefig.bbox'] = 'tight'


def main():	
	fig = plt.figure()
	ax = fig.add_axes((0,0,1,1))  # axes good, no margins
	ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize
	fig.set_size_inches(6,6)  # savefig with dpi=132, for a 600x600 image to match aerial
	stripBorder(fig,ax)
	plt.xlim(-132,+132)
	plt.ylim(-132,+132)
	draw(ax)
	fig.savefig(fname_localtemp)
	plt.show()

if __name__ == '__main__':
	main()
