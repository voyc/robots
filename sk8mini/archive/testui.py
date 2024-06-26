''' 
testui.py  
	x matplotlib
	x non-blocking
	x animation
	x save still
	save movie

FuncAnimation blocks.
Therefore it is only useful in a standalone drawing program.
I wanted to add a UI onto an existing robot controller program.
I did it by using Artists and pause().
An Artist's attributes can be changed, and then pause() will redraw all the Artists.
Other than that, there is no consistency in the way Artists are defined, created, or modified.

plt.pause()
	source: https://matplotlib.org/3.4.3/_modules/matplotlib/pyplot.html

	The pause() method does three things:
		1. redraw all the artists
		2. run the gui event loop
		3. sleep
	
	None of these display commands are necessary:
			plt.ion()
			plt.show(block=False)
			fig.canvas.draw()
			ax.draw_artist(artists)

matplotlib.artist.Artist

a tree of the subclasses of Artist
https://www.typeerror.org/docs/matplotlib~3.1/artist_api

Patch is a subclass of Artist

These shapes are subclasses of Patch:
	Circle
	Arc
	Rectangle

These are direct subclass of Artist:
	Text
	Line2D

plt.plot() - plots either linesegs or points (markers)
plt.scatter() - similar to plot()
	linesegs
	points

'''

import matplotlib
import matplotlib.pyplot as plt
import time
import numpy as np
import math

import nav
import specs

# global constants
fps = 20
ui_delay = 1/fps  # .05
ui_pause = .001

skate_refresh_time = 0.0
skate_speed = 30
skate_delay = 1/skate_speed

fname = 'arena_%timestamp%.png'


aCones = [
	[0,+100], # top
	[0,-100], # bottom
	[-100,0], # left
	[+100,0], # right
	[0,0]     # center
]

aRoute = [
	{
		'shape':'line',
		'from': [-110,-110],
		'to':[-23,100],
	},
	{
		'shape':'arc',
		'from':[-23,100],
		'to':[23,100],
		'center':[0,100],
		'rdir':'cw',
	},
	{
		'shape':'line',
		'from': [23,110],
		'to':[23,-100],
	},
	{
		'shape':'arc',
		'from':[23,-100],
		'to':[0,-123],
		'center':[0,-100],
		'rdir':'cw',
	},
	{
		'shape':'line',
		'from': [0,-123],
		'to':[-110,-110],
	},
]
		
gArenaBox = [0,0,600,600]		# graphics
aArenaBox = [-132,+132,132,-132]	# analog

aDonut = [-110,-110]
aGate = [-110,-110]

heading = 335

pxPerCm = 2.27  # 150 cm = 340 pixels, using photo of tape measure
cmPerPx = .44
gArenaCenterX = int((gArenaBox[2] - gArenaBox[0]) / 2)
gArenaCenterY = int((gArenaBox[3] - gArenaBox[1]) / 2)

# global variables
running = True
conesChanged = True
routeChanged = True
donutChanged = True
ui_refresh_time = 0.0

# artists
fig = None
ax = None
class UI:
	skate = None
	cones = []
	conetexts = []
	legs = []
ui = UI()


def onpress(event):
	global running, aCones, conesChanged
	if event.key == 'c':
		print('UI: save image')
		ts = time.strftime("%Y%m%d-%H%M%S")
		fig.savefig(fname.replace('%timestamp%', ts))
	if event.key == '1':
		print('UI: 1 change cones')
		aCones = specs.vcones['square']
		conesChanged = True
	if event.key == '2':
		print('UI: 2 change cones')
		aCones = specs.vcones['iron-cross']
		conesChanged = True
	if event.key == 'left':
		print('UI: turn left')
	if event.key == 'right':
		print('UI: turn right')
	if event.key == 'up':
		print('UI: go straight')
	if event.key == 'q':
		print('UI: kill')
		running = False
	if event.key == 'ctrl+c':
		print('UI: kill interrupt')
		running = False

def pilot():
	global aDonut, donutChanged, skate_refresh_time
	if time.time() - skate_refresh_time < skate_delay:
		return
	aDonut[0] += 1
	aDonut[1] += 1
	donutChanged = True
	skate_refresh_time = time.time()

def startUI():
	global fig, ax, skateline, cones, conetexts, aRoute, routeChanged

	# setup artists
	fig, ax = plt.subplots()
	plt.xlim(-132,+132)
	plt.ylim(-132,+132)
	plt.autoscale(False)  # if True it will adapt x,ylim to the data
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize
	fig.canvas.mpl_connect('key_press_event', onpress) # keypress event handler

	# skate
	skateline = plt.gca().scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])

	#skatebox = matplotlib.patches.Rectangle((50, 100), specs.deck_length, specs.deck_width, linewidth=1, edgecolor='black', facecolor='black')
	#skatebox2 = matplotlib.patches.Rectangle((50, 100), specs.deck_length, specs.deck_width, linewidth=1, edgecolor='black', facecolor='black')
	#t2 = matplotlib.transforms.Affine2D().rotate_deg(-45) + ax.transData
	#skatebox2.set_transform(t2)
	#ax.add_patch(skatebox)
	#ax.add_patch(skatebox2)

	# cones
	for pt in aCones:
		circ = plt.Circle(pt, 10, color='y')
		ax.add_artist(circ)
		ui.cones.append(circ)
		t = plt.text(pt[0], pt[1], str(len(ui.cones)), fontsize='12', ha='center', va='center', color='black')
		ui.conetexts.append(t)
		
	# route legs
	for leg in aRoute:
		if leg['shape'] == 'line':
			A = (leg['from'])
			B = (leg['to'])
			xd,yd = np.transpose([A,B]); 
			linesegs = plt.plot(xd,yd, color='black', lw=1) # returns list of line2D objects
			ui.legs.append(linesegs[0])
		elif leg['shape'] == 'arc':
			A = (leg['from'])
			B = (leg['to'])
			C = (leg['center'])
			tA,_ = nav.thetaFromPoint(A, C)
			tB,_ = nav.thetaFromPoint(B, C)
			rdir = leg['rdir']
			r = 23
			t1 = tA
			t2 = tB
			if rdir == 'cw': 
				t1 = tB
				t2 = tA
				if t1 == t2:
					t2 -= .001
			arc = matplotlib.patches.Arc(C, r*2, r*2, 0, math.degrees(t1), math.degrees(t2), color='black')
			ax.add_patch(arc)
			ui.legs.append(arc)
		routeChanged = True

	running = True

def refreshUI():
	global conesChanged, routeChanged, donutChanged, cones, conetexts, aRoute, ui_refresh_time, skateline

	if time.time() - ui_refresh_time < ui_delay:
		return

	if conesChanged:
		i = 0
		for i in range(len(ui.cones)):
			ui.cones[i].center = aCones[i]
			ui.conetexts[i]._x = aCones[i][0]
			ui.conetexts[i]._y = aCones[i][1]
		conesChanged = False

	if routeChanged:
		for i in range(len(aRoute)):
			leg = aRoute[i]
			if leg['shape'] == 'line':
				A = (leg['from'])
				B = (leg['to'])
				xd,yd = np.transpose([A,B]); 
				ui.legs[i].set_data(xd,yd)
	
		for leg in aRoute:
			if leg['shape'] == 'arc':
				A = (leg['from'])
				B = (leg['to'])
				C = (leg['center'])
				tA,_ = nav.thetaFromPoint(A, C)
				tB,_ = nav.thetaFromPoint(B, C)
				rdir = leg['rdir']
				r = 23
				nav.drawArc(tA ,tB, rdir, C, r)
		routeChanged = False

	if donutChanged:
		bow,stern = nav.lineFromHeading(aDonut, heading, specs.deck_length/2)
		diff = (bow - stern) / 5  # add 4 dots between bow and stern
		points = [0,0,0,0,0]
		for i in range(5): points[i] = stern + (diff * i)
		skateline.set_offsets(points)
		donutChanged = False

	plt.pause(ui_pause)  # redraw and time.sleep()
	ui_refresh_time = time.time()

def main():
	global aDonut, donutChanged
	startUI()
	refreshUI()

	# main loop
	while running:
		pilot()
		refreshUI()

	plt.close()

if __name__ == '__main__':
	main()

