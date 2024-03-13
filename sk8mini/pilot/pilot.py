'''
pilot.py
virtual joystick to control sk8mini via http

http://192.168.1.100:8080/throttle?start
http://192.168.1.100:8080/throttle?kill

http://192.168.1.100:8080/throttle?ahead=10
http://192.168.1.100:8080/throttle?astern=10
http://192.168.1.100:8080/throttle?stop=0

http://192.168.1.100:8080/helm?starboard=10
http://192.168.1.100:8080/helm?port=10
http://192.168.1.100:8080/helm?amidships=0
'''

import curses
import requests
 
screen = curses.initscr() # get the curses screen window
curses.noecho() # turn off input echoing
curses.cbreak() # respond to keys immediately (don't wait for enter)
screen.keypad(True) # map arrow keys to special values

helm = 0
throttle = 0
adjthrottle = 0
maxthrottle = 9
maxhelm = 9
opthelm = 5
savhelm = 0
savthrottle = 0

'''
1. turn on the awacs first to create the network
2. turn on the sk8
3. connect laptop to browser
4. can test url in browser
5. samantha chat also uses port 8080, and if it is running, which it should not be, it causes conflict
'''
#baseurl = 'http://192.168.1.100:8080'
baseurl = 'http://192.168.4.2:8080'
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
		value = value * 10  # times ten to get degrees: 0 to +-90
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
		screen.addstr(y, 30, 'no response from http') 
	linenum = linenum + 1
	if linenum > maxline:
		linenum = minline

def start():
	global throttle, helm
	throttle = 0
	helm = 0
	send("start")

def kill():
	global throttle, helm
	throttle = 0
	helm = 0
	send("kill")

	send("throttle?stop")
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

		elif char == curses.KEY_SRIGHT:
			helm = opthelm
		elif char == curses.KEY_SLEFT:
			helm = -opthelm
		elif char == curses.KEY_SR:  # SF
			helm = 0

		elif char >= ord('1') and char <= ord('9'):
			opthelm = int(chr(char))
			continue;
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

