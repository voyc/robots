'''
replay.py
'''

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import specs
import glob

data_extent = [-132,132,-132,132]
basedir = 'photos/2024*/'
fps = 5
delay = 1/fps
paused = False
killed = False

def onpress(event):
	global paused, killed
	if event.key == 'p':
		paused = not paused
	if event.key == 'q':
		killed = True

def startUI():
	# setup artists
	fig = plt.figure()
	ax = fig.add_axes((0,0,1,1))

	plt.xlim(-132,+132)
	plt.ylim(-132,+132)

	plt.autoscale(False)  # if True it will adapt x,ylim to the data
	ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize

	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False) 
	plt.tick_params(axis='y', which='both', right=False, left=False, labelleft=False) 
	  
	fig.canvas.mpl_connect('key_press_event', onpress) # keypress event handler

	fig.set_size_inches(6, 6)
	return fig, ax

def main():	
	import sys
	lastdir = ''
	if len(sys.argv) > 1:
		lastdir = sys.argv[1]
	else:	
		dirs = glob.glob(basedir)
		lastdir = list(reversed(sorted(dirs)))[0]
	print(f'replay folder {lastdir}')

	# list of jpgs and pngs in order by timestamp embedded in the 
	pattern1 = f'{lastdir}*.jpg'
	pattern2 = f'{lastdir}*.png'

	files1 = glob.glob(pattern1)
	files2 = glob.glob(pattern2)

	files = files1 + files2
	files = sorted(files)

	# create two image objects, jpg underneath, transparent png on top
	fig, ax = startUI()
	fname = files[0] 
	mat = plt.imread(fname)
	imgJpg =  plt.imshow(mat, extent=data_extent)
	mat = plt.imread(fname)
	imgPng =  plt.imshow(mat, extent=data_extent)

	# loop thru all the files, replacing the data in the two image objects as we go
	filendx = 0
	loopdelay = delay
	while not killed:
		if filendx >= len(files):
			break
		if not paused:
			fname = files[filendx]
			print(fname)
			filendx += 1
			mat = plt.imread(fname)

			if 'jpg' in fname:
				imgJpg.set_data(mat)
				loopdelay = 0.001
			else:
				imgPng.set_data(mat)
				loopdelay = delay

		plt.pause(loopdelay)

if __name__ == '__main__':
	main()
