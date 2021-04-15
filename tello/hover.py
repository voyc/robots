'''
hover.py
combine tellomission.py with murtaza/color.py

color.py
	while
		read the frame
		ui: debug: get settings from trackbars
		detectObjects: cones, pads
		buildMap  -- getObjectData
		ui: drawMap
		ui: show the images
		q quits
	close windows

tellomission.py
	two loops, two threads, two sockets
		video - read frame, imshow(), q to quit
		telemetry - read telemetry data into a global dict
	sendCommand, also receives reply
	flymission
	quit

note: keep UI separate, because jetson version will not have it



The drone is name "eyes".
But it includes telemetry data input and flying ability.

What part of the brain builds maps and does spatial awareness?



'''


