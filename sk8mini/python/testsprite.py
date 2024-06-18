'''
testsprite.py
'''

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import specs

#
#
#class Sprite:
#	data = [
#		[ 0,11],
#		[ 6,11],
#		[ 6,16],
#		[10,16],
#	
#		#[10, 0],
#		[10, 5],
#		[15, 0],
#	
#		#[33, 0],
#		[28, 0],
#		[33, 5],
#	
#		[33,16],
#		[37,16],
#		[37,11],
#		[42,11],
#		[42,23],
#		[37,23],
#		[37,18],
#		[33,18],
#		[33,46],
#		[37,46],
#		[37,41],
#		[42,41],
#		[42,53],
#		[36,53],
#		[36,48],
#		[33,48],
#		[33,63],
#		[10,63],
#		[10,48],
#		[ 6,48],
#		[ 6,53],
#		[ 0,53],
#		[ 0,41],
#		[ 6,41],
#		[ 6,46],
#		[10,46],
#		[10,18],
#		[ 6,18],
#		[ 6,23],
#		[ 0,23],
#		[ 0,11]
#	]
#	pos = [0,0]
#	dim = [43,64]
#
#	def normalized():
#		# turn upside down and center
#		csprite = []
#		for pt in data:
#			csprite.append([pt[0]-21, (64-pt[1])-32])
#		return csprite
#


	#def extent(self):
	#	dim = self.dim
	#	return [self.pos[0]-dim[0]/2, self.pos[0]+dim[0]/2, \
        #        self.pos[1]-dim[0]/2, self.pos[1]+dim[1]/2]

class UI:
	fps = 20
	delay = .05
	fig = None
	ax = None
	sprite = None

def onpress(event):
	if event.key == 'q':
		quit()

def startUI():
	# setup artists
	ui = UI()
	ui.fig, ui.ax = plt.subplots()
	plt.xlim(-132,+132)
	plt.ylim(-132,+132)
	plt.autoscale(False)  # if True it will adapt x,ylim to the data
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	ui.ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize
	ui.fig.canvas.mpl_connect('key_press_event', onpress) # keypress event handler

	ui.sprite = matplotlib.patches.Polygon(specs.skateSprite, color='black')
	ui.ax.add_patch(ui.sprite)

	#t = matplotlib.transforms.Affine2D().translate(-22,-32)
	#tra = t + ui.ax.transData
	#ui.sprite.set_transform(tra)

	w = 43
	h = 64
	x = -50
	y = -50
	t = y - int(h/2)
	l = x - int(w/2)
	b = y + int(h/2)
	r = x + int(w/2)

	heading = 270


	for i in range(100):
		heading = i * 3.6
		x = i
		y = i
		ui.sprite.pos = [x,y]
		ui.sprite.hdg = heading 

		r = matplotlib.transforms.Affine2D().rotate_deg(360-heading)
		t = matplotlib.transforms.Affine2D().translate(x,y)
		tra = r + t + ui.ax.transData
		ui.sprite.set_transform(tra)

		plt.pause(.1)	
	



def main():
	startUI()


if __name__ == "__main__":
	main()

