'''
sk8minimath.py
'''

# throttle

# percent throttle: -100 to +100

int throttle  =  0;  // positive: ahead, negative: astern
int adjusted  =  0;  // throttle adjusted for helm position

const int aheadSlow =  3;   // throttle examples: 0,1,2 full stop
const int aheadHalf = 23;   // 23 -  3 = 20, 20/2 = 10 steps 
const int aheadFull = 43;   // 43 - 23 = 20
const int throttleInc =  2;     // reasonable increment throttle steps

# helm degrees -90 to +90
int helm = 0;  // positive: starboard, negative: port
int helmDesired = 0;
const int portFull = -90;
const int portHalf = -45;
const int portSlow =  -5;
const int starboardFull = 90;

const int starboardHalf = 45;
const int starboardSlow =  5;
const int helmAmidships =  0;

const int helmSweepInc = 2;
const int helmStepInc = 5;
const int helmPause = 10;


setPilot( 90, 23)
sleep.time(10)
setPilot( -90, 23)
sleep.time(10)
setPilot( 0, 0)



# dimensions and measurements:
wheel_diameter	=  5.4	# cm
wheel_circum	= 17.0  # cm (diameter * pi)
wheelbase 	= 13.0	# cm
wheeltrack	= 16.5	# cm
max_roll	= 19.0	# degrees (deck angle)

deck_width	= 10.0	# cm
deck_length	= 28.0	# cm
arm_length	=  5.4	# cm (distance between donut center and arm pivot)
arm_offset	= 11.0	# cm (distance of arm pivot astern of deck center)

# tightest turn, at max_roll: 
inner_wheelbase	=  8.0	# cm
outer_wheelbase	= 17.5	# cm
turning_radius	= 23.0	# cm
turning_circum	=144.5	# cm (radius * 2pi) 
axle_angle	= 10.0	# degrees 
deck_angle	= 19.0	# degrees
ycenter_offset	=  1.5	# cm (deck - wheelbase)

# arena (600x600 pixels):
arena_width	= 272.7	# cm (600 / pxPerCm) 
arena_height	= 272.7	# cm (600 / pxPerCm) 

# ratios:
pxPerCm = 2.2	# cm (22 pixels / 10 cm)
 

	throttle : speed : distance : roll adjustment
	helm : arm angle : roll
	roll : turning radius : axle angle : outer wheel speed : inner wheel speed
	roll : deck center : wheelbase center

	distance: cm, px, cm:px
	speed: cm/sec, px/sec

	angular velocity

https://www.geogebra.org/geometry/w3kqwan9
	turning radius inner = 23 - 8.25 = 14.75 * 2pi =  92.67
	turning radius center            = 23.00 * 2pi = 144.51
	turning radius outer = 23 + 8.25 = 31.25 * 2pi = 196.35


ctrWheelbase	(x,y)

def wheelbaseFromDonut(x,y):
	return x,y



throttle interpolate

input -100 to +100
output 0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,35,36,38,40

if input <= 3
	output = 0
else
	factor = 40 to 100
	output = input -3 * factor

throttle is always set to 50%
adjusted can be 0 or 4 to 43


https://calculator.academy/turning-radius-calculator/


