/* sk8servos.ino

board esp32:esp32:nano_nora
  the Arduino Nano ESP32, with the ESP32 from espressif, and the NORA-W106 module from u-blox

two servos: helm and throttle 
  using GPIO (espressif) pin numbers 6 and 9, PinNumbers=byGPIONumber
  (PinNumbers=default does a pin number remap and results in a compile error)
*/

#include <ESP32Servo.h>

/*
*
* helm
* DSservo 25KG servo motor 
* https://www.dsservo.com/en/d_file/DS3225%20datasheet.pdf
* pwm microseconds 500 to 2500, angle 0 to 180
*
*/
Servo servoHelm;
const int pinHelm = 6;  // D3==GPIO6  full strength input voltage from bat rail 6.6V - 8.4V
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

/* set the value of helm and write it to the servo */
void setHelm(int angle, boolean isadjust=true) {
	helm = angle;
	servoHelm.write(rotate(reverse(angle)));
	if (isadjust)
		adjustThrottle();
}
int getHelm() {
	return helm;
}

/* sweep the helm smoothly to its new position */
void sweepHelm(int angle, int dps=120) {
	// angle is the desired arm angle, as opposed to the deck angle
	// dps is the arm speed (angular velocity) in degrees per second
	//      between 90 and 180 is reasonable, 120 is ideal;  180: -45 to 45 in half second
	int inc = helmSweepInc;  // optimal increment of distance of each step
	int pause = helmPause;  // optimal pause between steps 

	int travel = angle - helm; // travel vector (distance) given by old and new angles
	if (travel < 0)   // let increment match the sign of the travel vector
		inc = 0 - inc;
	int ttime = (int)(abs(travel) * 1000) / dps; // travel time in ms varies with vector and velocity 
	int steps = (int)travel / inc; // vector and increment gives steps, rounded down
	pause = ttime / steps; // ttime and steps gives pause for each step, rounded down
	logger(50, "sweepHelm dps:%d, angle:%d, helm:%d, ttime:%d, steps:%d, pause:%d", dps, angle, helm, ttime, steps, pause);

	if (pause >= helmPause) { // if pause greater than minimum pause for sweep)
		int n = helm;
		for (int i=0; i<steps; i++) {
			n += inc;
			setHelm(n, false);
			delay(pause);
		}
	}
	adjustThrottle();
}

/* snap sk8 back to upright position */
void zeroHelm() {
	int newhelm = 10;
	if (helm > 0)
		newhelm = -10;
	setHelm(newhelm, false);
	delay(500);
	setHelm(0);
}

void checkHelm() {
	if (helmDesired != helm) {
		sweepHelm(helmDesired);
	}
}


/*
*
* throttle
* KOOKYE 360 degree continuous
* https://kookye.com/2016/02/01/kookye-360-degree-unlimited-rotation-micro-servo-motor-for-telecar-robot-helicopter/
* officially: pwm microseconds 500 to 2500, angle 0 to 180
* in fact: barely half this range is effective
* drive motor installed on right rear wheel
*
*/
Servo servoThrottle;
const int pinThrottle = 9;  // D6==GPIO9  6V regulated input, continuous servo
int throttle  =  0;  // positive: ahead, negative: astern
int throttleDesired  =  0;
int adjusted  =  0;  // throttle adjusted for helm position
const int aheadSlow =  3;   // throttle examples: 0,1,2 full stop
const int aheadHalf = 23;   // 23 -  3 = 20, 20/2 = 10 steps 
const int aheadFull = 43;   // 43 - 23 = 20
const int throttleInc =  2;     // reasonable increment throttle steps

/* set the value of throttle and write it to the servo */
void setThrottle(int angle, boolean isadjust=true) {
	if (abs(angle) < aheadSlow)
		angle = 0;
	throttle = angle;
	if (isadjust) 
		adjustThrottle();
	else {
		servoThrottle.write(rotate(reverse(angle)));
		adjusted = throttle;
	}
}
int getThrottle() {
	return throttle;
}
void zeroThrottle() {
	setThrottle(0, false);
}
	
void sweepThrottle(int angle, int dps=180) {
	if (abs(angle) < aheadSlow)
		angle = 0;
	int diff = angle - throttle;  // distance of travel is given by old and new angles
	// int dps = 180;  // angular velocity in degrees per second (180: -45 to 45 in half second)
	int inc = throttleInc;  // optimal increment: 2 degrees
	if (diff < 0)
		inc = 0 - inc;
	int pause = 10;  // optimal pause: 10 ms
	int ttime = (int)(diff * 1000) / dps; // travel time varies with distance and velocity 
	ttime = abs(ttime);
	int steps = (int)ttime / pause;
	logger(50, "sweepThrottle angle:%d, throttle:%d, ttime:%d, steps:%d", angle, throttle, ttime, steps);

	int n = throttle;
	for (int i=0; i<steps; i++) {
		n += inc;
		setThrottle(n,false);
		delay(pause);
	}
	setThrottle(angle); // remainder
}

void adjustThrottle() {
	adjusted = calcThrottleAdjustment(throttle, helm);
	if (abs(throttle) <= aheadSlow)
		adjusted = throttle;
	servoThrottle.write(rotate(reverse(adjusted)));
}

/* motor on right-rear wheel.  starboard helm: slow it down;  port helm: speed it up */
int calcThrottleAdjustment(int throttle, int helm) {
	int maxhelm = 45;
	int factor = (int)(helm*100) / maxhelm;
	int adj = (int)(factor * throttle)/100;
	int adjusted = throttle - adj;	
	if (throttle > 0) 
		adjusted = max(adjusted, aheadSlow);
	else if (throttle < 0) 
		adjusted = min(adjusted, -aheadSlow);
	logger(30, "calculate adjusted throttle: %d:%d, helm:%d, factor:%d, adj:%d", throttle, adjusted, helm, factor, adj);
	return adjusted;
}

void checkThrottle() {
	if (throttleDesired != throttle) {
		sweepThrottle(throttleDesired);
	}
}

/*
*
* utilities for both motors
*
*/

int reverse(int dgr) { return 0 - dgr; }  // both motors are installed upside down
int rotate(int dgr) { return dgr + 90; }  // incoming angle is -90 to +90.  servo expects 0 to 180
int unrotate(int dgr) { return dgr - 90; }
 
void setupServos() {
	servoHelm.attach(pinHelm);  // attach always returns 1
	servoThrottle.attach(pinThrottle);
	setHelm(0, false);
	setThrottle(0, false);
}

void warmupServos() {
	sweepHelm( 20); delay(300);
	sweepHelm(-20); delay(300);
	zeroHelm();     delay(300);
	sweepThrottle( 20); delay(300);
	sweepThrottle(-20); delay(300);
	zeroThrottle();
}


/*
*
* local testing
*
*/

#ifdef SK8SERVOS_TESTING

void setup() {
	setupLogger();
	logger(100, "\nbegin setup");
	setupServos();
	warmupServos();
	logger(100, "setup complete");
}

void loop() {
	delay(1000);
}
 
void testSim() {
	logger(100, "begin test sim");
	sweepThrottle(23); delay(3000);
	sweepHelm(    22); delay(3000);
	sweepHelm(    45); delay(3000);
	sweepHelm(     0); delay(3000);
	sweepHelm(   -22); delay(3000);
	sweepHelm(   -45); delay(3000);

	zeroThrottle();
	zeroHelm();
	logger(100, "end test sim");
}

void testOneThrottle(int angle) {
	logger( 50, "test one throttle %d", angle);
	sweepThrottle( angle);
	delay(3000);
}
void testThrottle() {
	logger(100, "begin test throttle");
	helm = 20;
	testOneThrottle(23);
	zeroThrottle();
	logger(100, "end test throttle");
}

void testThrottleAdjustmentCalculation() {
	logger(100, "begin test throttle adjustment calculation");
	calcThrottleAdjustment(10, 10);
	calcThrottleAdjustment(10, 20);
	calcThrottleAdjustment(10, 30);
	calcThrottleAdjustment(10, 40);
	calcThrottleAdjustment(10, -10);
	calcThrottleAdjustment(10, -20);
	calcThrottleAdjustment(10, -30);
	calcThrottleAdjustment(10, -40);

	calcThrottleAdjustment(40, 10);
	calcThrottleAdjustment(40, 20);
	calcThrottleAdjustment(40, 30);
	calcThrottleAdjustment(40, 40);
	calcThrottleAdjustment(40, -10);
	calcThrottleAdjustment(40, -20);
	calcThrottleAdjustment(40, -30);
	calcThrottleAdjustment(40, -40);
	logger(100, "end test throttle adjustment calculation");
}

void testHelm() {
	logger(100, "begin test helm");
	logger(30, "test helm min:%d, max:%d", MIN_PULSE_WIDTH, MAX_PULSE_WIDTH);
	logger(30, "test helm angle:%d, ms:%d", servoHelm.read(), servoHelm.readMicroseconds());

	int helmangle = 50;  // 10 to 50
	int sweepspeed = 120;  // 90 to 180

	sweepspeed = 180;  // 90 to 180
	sweepHelm( 10, sweepspeed); delay(3000);
	sweepHelm( 20, sweepspeed); delay(3000);
	sweepHelm( 30, sweepspeed); delay(3000);
	sweepHelm( 40, sweepspeed); delay(3000);
	sweepHelm( 50, sweepspeed); delay(3000);
	sweepHelm( 40, sweepspeed); delay(3000);
	sweepHelm( 30, sweepspeed); delay(3000);
	sweepHelm( 20, sweepspeed); delay(3000);
	sweepHelm( 10, sweepspeed); delay(3000);
	sweepHelm(  0, sweepspeed); delay(3000);
	sweepHelm( 50, sweepspeed); delay(3000);
	sweepHelm(  0, sweepspeed); delay(3000);
	sweepHelm(-10, sweepspeed); delay(3000);
	sweepHelm(-20, sweepspeed); delay(3000);
	sweepHelm(-30, sweepspeed); delay(3000);
	sweepHelm(-40, sweepspeed); delay(3000);
	sweepHelm(-50, sweepspeed); delay(3000);
	sweepHelm( 50, sweepspeed); delay(3000);
	sweepHelm(-50, sweepspeed); delay(3000);
	sweepHelm(-40, sweepspeed); delay(3000);
	sweepHelm(-30, sweepspeed); delay(3000);
	sweepHelm(-20, sweepspeed); delay(3000);
	sweepHelm(-10, sweepspeed); delay(3000);
	zeroHelm();
	logger(100, "end test helm");
}
#endif
