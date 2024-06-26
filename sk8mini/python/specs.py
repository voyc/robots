'''
specs.py

for turning radius see: 
~/media/webapps/sk8mini/awacs/photos/20240613-074007/2024613.xcv

'''

# dimensions and measurements:
wheel_diameter	=  5.4	# cm
wheel_circum	= 17.0  # cm (diameter * pi)
wheel_width	=  2.6  # cm
wheelbase 	= 13.0	# cm
wheeltrack	= 16.5	# cm
max_roll	= 19.0	# degrees (deck angle)

overall_width	= 19.1	# cm (wheeltrack + 1 wheel width)
deck_width	= 10.0	# cm
deck_length	= 28.0	# cm
helm_length	=  5.4	# cm (distance between donut center and arm pivot)
helm_offset	= 11.0	# cm (distance of arm pivot astern of deck center)
helm_bias	= -19.0 # degrees (value required for straight-line travel)

# tightest turn, at max_roll: 
inner_wheelbase	=  8.0	# cm
outer_wheelbase	= 17.5	# cm
turning_radius	= 23.7	# cm
turning_circum	=144.5	# cm (radius * 2pi) 
axle_angle	= 10.0	# degrees 
deck_angle	= 19.0	# degrees
ycenter_offset	=  1.5	# cm (deck - wheelbase)

cone_diameter	= 8	# cm or 18px
cbase_to_donut_edge = 14.5 # cm
between_donut_and_cone = 5.2	# cm (23.7 - 4 - 14.5)

donut_inner_dia	=  5 #  cm
donut_outer_dia	= 10 # cm

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

#def awacs2gcs(pt):
#	return [pt[0], 600-pt[1]]

def awacs2skate(pt):
	#return [(pt[0] - 300) * cmPerPx, (0-pt[1] - 300) * cmPerPx]
	return [(pt[0] - 300) * cmPerPx, (600-pt[1] - 300) * cmPerPx]

#def skate2gcs(pt):
#	return pt  
#	# [int(pt[0] * pxPerCm + 300), int(pt[1] * pxPerCm + 300)]

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

# sim arena data
vcones = {
'iron-cross': [
	[0,+100], # top
	[0,-100], # bottom
	[-100,0], # left
	[+100,0], # right
	[1,1]     # center
],
'square': [
	[-100,+100], # NW
	[+100,+100], # NE
	[+100,-100], # SE
	[-100,-100], # SW
	[1,1]	     # Center
],
}

#skateSpriteDataPx = [
#	[ 0,11],
#	[ 6,11],
#	[ 6,16],
#	[10,16],
#
#	#[10, 0],
#	[10, 5],
#	[15, 0],
#
#	#[33, 0],
#	[28, 0],
#	[33, 5],
#
#	[33,16],
#	[37,16],
#	[37,11],
#	[42,11],
#	[42,23],
#	[37,23],
#	[37,18],
#	[33,18],
#	[33,46],
#	[37,46],
#	[37,41],
#	[42,41],
#	[42,53],
#	[36,53],
#	[36,48],
#	[33,48],
#	[33,63],
#	[10,63],
#	[10,48],
#	[ 6,48],
#	[ 6,53],
#	[ 0,53],
#	[ 0,41],
#	[ 6,41],
#	[ 6,46],
#	[10,46],
#	[10,18],
#	[ 6,18],
#	[ 6,23],
#	[ 0,23],
#	[ 0,11]
#]
#
#skateSpriteDim = [43,64]
#skateSprite = []
#
#for pt in skateSpriteData:
#	skateSprite.append([pt[0]-21, (64-pt[1])-32])

skateSpriteRaw = [
	[0	,4.84 ],
	[2.64	,4.84 ],
	[2.64	,7.04 ],
	[4.4	,7.04 ],
	[4.4	,2.2 ],
	[6.6	,0 ],
	[12.32	,0 ],
	[14.52	,2.2 ],
	[14.52	,7.04 ],
	[16.28	,7.04 ],
	[16.28	,4.84 ],
	[18.48	,4.84 ],
	[18.48	,10.12 ],
	[16.28	,10.12 ],
	[16.28	,7.92 ],
	[14.52	,7.92 ],
	[14.52	,20.24 ],
	[16.28	,20.24 ],
	[16.28	,18.04 ],
	[18.48	,18.04 ],
	[18.48	,23.32 ],
	[15.84	,23.32 ],
	[15.84	,21.12 ],
	[14.52	,21.12 ],
	[14.52	,27.72 ],
	[4.4	,27.72 ],
	[4.4	,21.12 ],
	[2.64	,21.12 ],
	[2.64	,23.32 ],
	[0	,23.32 ],
	[0	,18.04 ],
	[2.64	,18.04 ],
	[2.64	,20.24 ],
	[4.4	,20.24 ],
	[4.4	,7.92 ],
	[2.64	,7.92 ],
	[2.64	,10.12 ],
	[0	,10.12 ],
	[0	,4.84 ],
]

skateSpriteDim = [19.1, 28]
skateSprite = []

for pt in skateSpriteRaw:
	skateSprite.append([pt[0]-(skateSpriteDim[0]/2), (skateSpriteDim[1]-pt[1])-(skateSpriteDim[1]/2)])

