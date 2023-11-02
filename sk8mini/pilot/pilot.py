import curses
import requests
 
# get the curses screen window
screen = curses.initscr()
 
# turn off input echoing
curses.noecho()
 
# respond to keys immediately (don't wait for enter)
curses.cbreak()

# map arrow keys to special values
screen.keypad(True)
 

helm = 0
throttle = 0
maxthrottle = 9
maxhelm = 9
savhelm = 0
savthrottle = 0

baseurl = 'http://192.168.1.100:8080'
linenum = 27
minline = 27
maxline = 37

def clamp(v,n,x):   # value, min, max
	return max(n, min(x, v))

def draw():
	for y in range((maxthrottle*2)+1):
		screen.addstr(y, 0, '                  |                  ')
	for x in range((maxhelm*4)+1):
		screen.addstr(maxthrottle, x, '-')
	screen.addstr(maxthrottle, maxhelm*2, '+')

	sthrottle = (maxthrottle * 2) - (throttle + maxthrottle)
	shelm = (helm + maxhelm) * 2

	screen.addstr(sthrottle, shelm, 'o')

	screen.addstr(22, 0, f'helm {helm}    ') 
	screen.addstr(23, 0, f'throttle {throttle}    ') 
	screen.addstr(25, 0, f'q to quit') 

def compose():
	cmd = ''
	name = ''
	value = ''
	qs = ''
	if savhelm != helm:
		cmd = 'helm'
		if helm < 0:
			name = 'port'
			value = 0 - helm
		elif helm == 0:
			name = 'amidships'
			value = 0
		else:
			name = 'starboard'
			value = helm
	elif savthrottle != throttle:
		cmd = 'throttle'
		if throttle < 0:
			name = 'astern'
			value = 0 - throttle
		elif throttle == 0:
			name = 'stop'
			value = 0
		else:
			name = 'ahead'
			value = throttle
	if cmd:
		value = value * 10
		qs = f'{cmd}?{name}={value}'
	return qs

def send(qstring):
	global linenum
	url = f'{baseurl}/{qstring}'
	y = linenum
	screen.addstr(y, 0, url) 
	try:
		response = requests.get(url)	
	except:
		screen.addstr(y, 30, 'vehicle offline') 
	linenum = linenum + 1
	if linenum > maxline:
		linenum = minline

def kill():
	global throttle, helm
	throttle = 0
	send("throttle?stop")
	helm = 0
	send("helm?amidships")

try:
	draw()
	while True:
		savhelm = helm
		savthrottle = throttle
		char = screen.getch()
		if char == ord('q'):
			kill()
			break
		elif char in [10,13,curses.KEY_ENTER]:
			kill()
			draw()
			continue
		elif char == curses.KEY_RIGHT:
			helm += 1
		elif char == curses.KEY_LEFT:
			helm -= 1
		elif char == curses.KEY_UP:
			throttle += 1
		elif char == curses.KEY_DOWN:
			throttle -= 1
		else:
			continue

		throttle = clamp(throttle, 0-maxthrottle, maxthrottle)
		helm = clamp(helm, 0-maxhelm, maxhelm)
		draw()
		qstring = compose()
		send(qstring)

finally:
	# shut down cleanly
	curses.nocbreak() 
	screen.keypad(0) 
	curses.echo()
	curses.endwin()

'''

helm port 45
helm starboard 60
helm amidships 0

throttle ahead 50
throttle astern 22 
throttle stop 0

battery check

return a json string with telemetry data

'''

