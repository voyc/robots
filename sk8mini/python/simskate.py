''' 
simskate.py  

analog:
	forward movement per helm - real, mechanical
	manual controls or autopilot

sim: 
	forward movement per helm - modeled 
	manual controls or autopilot

experiments:
	1. how fast can we send helm commands?
	2. what is relationship between helm and deck_angle?	

simplified
	skip dead reckoning, go with photo only
	if photo not received after 3 seconds, stop vehicle and wait for new photo
	onPhoto
		take timestamp
		get latest roll and heading from sensor
		helm, speed are known
		record new position
		calc new bearing
		calc and set helm
		record all in captains_log
		display new situation on UI
'''

def skate_main:
	while True: if isKilled(): break
		if hasNewPhoto():
			pilot()	
			refreshUI()
		if isPhotoLate():
			stopSkate()
		if isSkateStopped():
			restartSkate()

def pilot():   simplified logic with no dead reckoning
	take timestamp
	get latest roll and heading from sensor
	helm, speed are known
	record new position
	calc new bearing
	calc and set helm
	record all in captains_log
	display new situation on UI

	skatestate, newhelm
	return newhelm

class State
	ts	= 0.0	# from clock
	pos 	= [0,0]	# from awacs
	head 	= 0	# from ahrs
	roll   	= 0	# from ahrs
	bear 	= 0	# per navigator
	helm   	= 0	# per navigator
	sped   	= 0	# per navigator
state = State()

def pilot():
	prev = copy.deepcopy(state)
	state.ts = time.time()
	state.pos = getPositionFromDonut(donut, state.head, state.roll, state.helm)
	state.head = ahrs.heading
	state.roll = ahrs.roll
	navigate(state, prev)  # calc bear, helm, sped






import matplotlib.pyplot as plt
import time
import nav
import specs

# global constants
fps = 20
ui_delay = 1/fps
pilot_cycle_time = 0.2  # seconds
ui_cycle_time = 0.2  # seconds

gArenaBox = [0,0,600,600]		# graphics
aArenaBox = [-132,+132,132,-132]	# analog

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
		
aDonut = [-110,-110]
aGate = [-110,-110]


# current state
timestamp = 0           #  
position = [0.0,0.0]	# discovered from object detection, or dead-reckoning
helm = 0		# deliberately set
roll = 0		# measured by ahrs
heading = 335		# measured by ahrs


# global variables
running = True
conesChanged = True
routeChanged = True
donutChanged = True

# artists
fig = None
ax = None
skateline = None

helm = 0
helm_bias = -19

# variables
previous_pilot_cycle = 0.0
previous_ui_cycle = 0.0


def calcNewPosition(prev_pos, prev_time, prev_head):
	newtime = time.time()
	elapsed = newtime - prev_time
	distance = elapsed * specs.speed 
	new_position = nav.reckonLine(prev_pos, cur_heading, distance)

	how long at this heading
	rudder = elapsed * helm
	new_head = prev_head + (elapsed * rudder)
	return newpos, newtime

def calcNewHeading(prev_heading):
	pos time
	helm time

	helm: 0 to 90 degrees
	deck_angle: 0 to 19 degrees
	axle_angle: 0 to 10 degrees
	rudder = axle_angle * 2

	rudder = deck_angle / 2 * 2	# coincidentally, deck_angle == rudder
	therefore rudder is proportional to helm
	0/90 : 0/20
rudder_helm = 20/90 = .22

	rudder = helm * rudder_helm
	deck_angle == roll
	in real life: helm affects deck_angle, which is measured precisely as roll

	roll == deck_angle == rudder

	if mode == 'real':
		when roll changes, rudder 
			set rudder to roll
	if mode == 'sim':
		simulate a roll event when helm changes
	onRoll(roll):
		rudder = roll
	in captainslog,
		record roll to helm over time so we can see the pattern

def onHelm(helm):
	rudder = pass

def onRoll(roll):
	rudder = roll

def onHeading(heading):
	captains_log(time, pos, helm, roll, heading)
	latency: helm -> roll -> heading	

	
def setHelm(incr):
	#helm = helm + incr	
	pass

	
def setHelm(incr):
	#helm = helm + incr	
	pass

def deadReckon()
	pass

def modelForwardMovement():
	# helm to heading in 4 steps
	helm
	deck_angle  helm * proprotion * time, n seconds to get to the new angle
	axle_angle = immediatey proportional to the deck angle
	rudder = 2 * axle_angle   # twice the axle angle (because there are two axles)
	heading = change every cycle based on rudder and time elapsed

if helm = 25
	over next 3 seconds, deck_angle goes to (25/90) * 90
	axle_angle = deck_angle * 1.9
	turning_radius = max_turning_radius * axle_angle
	heading = previous_heading + (previous_heading * axle_angle), delayed by one cycle

	# model the sk8mini
	deck_angle =		# helm influences deck angle
	axle_angle = 		# axle_angle directly proportional to deck angle
	turning_radius		# turning_radius directly proportional to axle_angle
	heading			# heading changes over time at given turning_radius

	# speed, heading, time
	pass

def drift():
	#throw in random errors in heading, due to 
	#		wind, incline, uneven surface, sloppy mechanics
	pass

def onpress(event):
	global running
	if event.key == 'c':
		print('UI: save image')
		ts = time.strftime("%Y%m%d-%H%M%S")
		fig.savefig(fname.replace('%timestamp%', ts))

	if event.key == 'left':
		print('UI: helm port')
		helm += 1
	if event.key == 'right':
		print('UI: helm starboard')
		helm -= 1
	if event.key == 'up':
		print('UI: helm amidships')
		helm = 0
	if event.key == 'q':
		print('UI: kill')
		running = False
	if event.key == 'ctrl+c':
		print('UI: kill interrupt')
		running = False
	
def startUI():
	global fig, ax, skateline

	# create artists
	fig, ax = plt.subplots()
	skateline = plt.gca().scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])

	plt.xlim(-132,+132)
	plt.ylim(-132,+132)
	plt.autoscale(False)  # if True it will adapt x,ylim to the data
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	ax.set_aspect('equal', anchor='C')  # keep fixed aspect ratio on window resize
	fig.canvas.mpl_connect('key_press_event', onpress) # keypress event handler

	running = True

def refreshUI():
	global conesChanged, routeChanged, donutChanged

	if conesChanged:
		i = 0
		for pt in aCones:
			x,y = (pt)
			print(x,y)
			circle1 = plt.Circle((x, y), 10, color='y')
			plt.gca().add_patch(circle1)
			plt.text(x, y, str(i+1), fontsize='12', ha='center', va='center', color='black')
			i += 1
		conesChanged = False

	if routeChanged:
		for leg in aRoute:
			if leg['shape'] == 'line':
				A = (leg['from'])
				B = (leg['to'])
				nav.drawLine([A,B])
	
			elif leg['shape'] == 'arc':
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
		global skateline
		bow,stern = nav.lineFromHeading(aDonut, heading, specs.deck_length/2)
		diff = (bow - stern) / 5  # add 4 dots between bow and stern
		points = [0,0,0,0,0]
		for i in range(5): points[i] = stern + (diff * i)
		skateline.set_offsets(points)

	plt.pause(.001)  # redraw

def pilot():
	global current_position, current_time, current_heading
	current_position, current_time = calcNewPosition( current_position, current_time, current_heading)
	current_heading = calcNewHeading(current_heading, rudder)

def pilot_cycle():
	global previous_pilot_cycle
	rc = False
	tm = time.time()
	if tm - previous_pilot_cycle > pilot_cycle_time:
		previous_pilot_cycle = tm
		rc = True
	return rc

def ui_cycle():
	global previous_ui_cycle
	rc = False
	tm = time.time()
	if tm - previous_ui_cycle > ui_cycle_time:
		previous_ui_cycle = tm
		rc = True
	return rc

def main():
	startUI()
	refreshUI()

	# main loop
	while running:
		if pilot_cycle():
			pilot()

		if ui_cycle():
			refreshUI()

	plt.close()

if __name__ == '__main__':
	main()

