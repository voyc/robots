'''
sk8mini_specs.py
'''

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



# arena cm measured in advance, fed to gcs via cli-args
wArenaCm = 272.7	# cm (600 / pxPerCm) 
hArenaCm = 272.7	# cm (600 / pxPerCm) 

# arena px determined by awacs altitude, changes with every photo
wArenaPx = 600
hArenaPx = 600

# px:cm ratio, determined by camera altitude
pxPerCm = 2.27  # 150 cm = 340 pixels, using photo of tape measure
cmPerPx = .44

# arena in cm

# arena in pixels
orientationArena = 0  # heading of up
centerArena = [0,0]
xArenaMin = centerArena[0] - int(wArenaCm/2)
xArenaMax = centerArena[0] + int(wArenaCm/2)
yArenaMin = centerArena[1] - int(hArenaCm/2)
yArenaMax = centerArena[1] + int(hArenaCm/2)




'''
	throttle : speed : distance : roll adjustment
	helm : arm angle : roll
	roll : turning radius : axle angle : outer wheel speed : inner wheel speed
	roll : deck center : wheelbase center

	distance: cm, px, cm:px
	speed: cm/sec, px/sec

	angular velocity

https://www.geogebra.org/geometry/w3kqwan9
	turning radius inner = 23 - 8.25 = 14.75 * 2pi =  92.67 = circum
	turning radius center            = 23.00 * 2pi = 144.51
	turning radius outer = 23 + 8.25 = 31.25 * 2pi = 196.35

inner_circum  =  92.67 # cm
center_circum = 144.51 # cm
outer_circum  = 196.35 # cm

# motor is on right rear wheel

# at throttle 23, speed is 144 cm/ n secs

# for one full circle
# wheel circum 17
# at right turn,    right wheel outer rim travels  92 cm,  92/17 =  5.4 revs
# on straight-away, right wheel outer rim travels 144 cm, 144/17 =  8.5 revs 
# at left turn,     right wheel outer rim travels 196 cm, 196/17 = 11.5 revs

#  5.4/8.5
# 11.5/8.5

# (144-92)/144 = .361
# (196-144)/144 = .361
# ( 8.5-5.4)/8.5 = .365
# (11.5-8.5)/8.5 = .353

# percent farther in the same time period


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


-----------------------
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
'''

'''
pid controller
PV process variable, roll
r(t) = set point: 0
y(t) = measurement: ahrs.roll
e(t) = error: r(t) - y(t)
u(t) = control variable, output: helm, set to weighted sum of P,I,D
Kp = proportional 
Ki = integral
Kd = derivative

P = Kp * e(t)

CV = u = (Kp * error) + (Kd * (dError / dt)) + (Ki * areaError  (area + (Error * dt))

currently, vehicle has consistent list to starboard
task 1: find helm offset that results in a straight line

non-zero rudder results in steadily changing heading
zero rudder = helm + helm_offset

user wants to think helm is at zero, actually it is at the offset
if offset is 2, helm must be 2 to keep rudder at zero

helm offset => zero rudder => straight line


#
rudder_angle = axle_angle * 2
deck_angle  and rudder angle are remarkably close

axle is mounted at 45 degrees
straight-ahead, axle is perpendicular to deck
deck angle 19 => axle angle 10

direct connection between roll and rudder
roll = deck_angle
rudder = axle_angle * 2
rudder affects heading
helm throws the weight

roll:rudder interpolation
19:20
consideer it 20:20, ie 1:1


when going straight, we want the rudder at 0
if roll is 10
	bring it back to zero

PID step 1, keep rudder at 0
PID step 2, keep heading at bearing, both change with vehicle position

'''
