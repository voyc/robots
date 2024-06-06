'''
specs.py
'''

# dimensions and measurements:
wheel_diameter	=  5.4	# cm
wheel_circum	= 17.0  # cm (diameter * pi)
wheelbase 	= 13.0	# cm
wheeltrack	= 16.5	# cm
max_roll	= 19.0	# degrees (deck angle)

deck_width	= 10.0	# cm
deck_length	= 28.0	# cm
helm_length	=  5.4	# cm (distance between donut center and arm pivot)
helm_offset	= 11.0	# cm (distance of arm pivot astern of deck center)
helm_bias	= -19.0 # degrees (value required for straight-line travel)

def applyHelmBias(helm): return max(-90, helm + helm_bias)

# tightest turn, at max_roll: 
inner_wheelbase	=  8.0	# cm
outer_wheelbase	= 17.5	# cm
turning_radius	= 23.0	# cm
turning_circum	=144.5	# cm (radius * 2pi) 
axle_angle	= 10.0	# degrees 
deck_angle	= 19.0	# degrees
ycenter_offset	=  1.5	# cm (deck - wheelbase)



# arena cm measured in advance, fed to gcs via cli-args
wArenaCm = 272.7	# cm (600 / pxPerCm) 
hArenaCm = 272.7	# cm (600 / pxPerCm) 

# arena px determined by awacs altitude, changes with every photo
wArenaPx = 600
hArenaPx = 600

# px:cm ratio, determined by camera altitude
pxPerCm = 2.27  # 150 cm = 340 pixels, using photo of tape measure
cmPerPx = .44

# coordinate systems and conversions
# see ~/Document/coordinate_systems.xcv

# awacs: px, int,   origin left, top,      positive down
# gcs:   px, int,   origin left, bottom,   positive up
# skate: cm, float, origin center,center,  positive up     

# shared memory uses awacs coordinate system

def awacs2gcs(pt):
	return [pt[0], 600-pt[1]]

def awacs2skate(pt):
	#return [(pt[0] - 300) * cmPerPx, (0-pt[1] - 300) * cmPerPx]
	return [(pt[0] - 300) * cmPerPx, (600-pt[1] - 300) * cmPerPx]

def skate2gcs(pt):
	return [int(pt[0] * pxPerCm + 300), int(pt[1] * pxPerCm + 300)]

# throttle and speed

# throttle	speed
# 43		14.27
# 23		10.32
# 3		2.25

speed = 10.32

def speedFromThrottle(throttle):
	if throttle == 43:
		speed = 14.27
	if throttle == 23:
		speed = 10.32
	if throttle == 3:
		speed = 2.25
	return speed
