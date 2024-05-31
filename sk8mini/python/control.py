'''
control.py 

PID controller

PV = process variable = roll
CV = control variable = helm

r(t) = set point: 0
y(t) = measurement: ahrs.roll
e(t) = error: r(t) - y(t)
u(t) = control variable, output: helm, set to weighted sum of P,I,D

Kp = proportional 
Ki = integral
Kd = derivative

This math is a cheat given by Paul McWhorter here:
https://www.youtube.com/watch?v=t7ImNDOQIzM&t=3s
at 49:38

The real deal should use calculus.
Also, Paul makes an error: he accumulates error-area infinitely.
Then to mitigate, he turns down Ki to .0001, to effetively take this term out of the equation.
'''

Kp = 0
Ki = 0
Kd = 0
eOld = 0
tOld = 0

def pidSetup(P, I, D):
	global Kp, Ki, Kd, eOld, tOld
	eOld = 0
	tOld = time.time()
	Kp = P
	Ki = I
	Kd = D

def pid(setpoint, actual, t):
	global eOld, tOld
	eNew = setpoint - actual
	tNew = t	
	dt = tNew - tOld
	dE = eNew - eOld
	slopeE = dE/dt
	areaE += eNew * dt	

	CV = (Kp * eNew) + (Kd * slopeE) + (Ki * areaE)

	eOld = eNew
	tOld = tNew
	return CV

