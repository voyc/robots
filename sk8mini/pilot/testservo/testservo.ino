#include <ESP32Servo.h>

/* board esp32:esp32:nano_nora
  the Arduino Nano ESP32, with the ESP32 from espressif, and the NORA-W106 module from u-blox  */

/* two servos: helm and throttle 
using GPIO (espressif) pin numbers 6 and 9, PinNumbers=byGPIONumber
(PinNumbers=default does a pin number remap and results in a compile error) */

Servo servoHelm;
int pinHelm = 6;  // D3==GPIO6  full strength input voltage from bat rail 6.6V - 8.4V
int helm = 0;

Servo servoThrottle;
int pinThrottle = 9;  // D6==GPIO9  6V regulated input, continuous servo
int throttle = 0;
int adjThrot = 0;  // adjusted gross throttle

/* incoming angle is -90 to +90.  servo expects 0 to 180 */
int rotate(int dgr) { return dgr + 90; }
int unrotate(int dgr) { return dgr - 90; }
 
/* log to serial port */
boolean logging = false;  // set true if Serial connected
int loglevel = 50;  // set by programmer

void logger(int level, char* msg, ...) {
	if (logging && (level >= loglevel)) {
		char buffer[80];
		va_list va;
		va_start (va, msg);
		vsprintf (buffer, msg, va);
		va_end (va);
		Serial.println(buffer);
	}
}

void jerkHelm(int angle) {
	servoHelm.write(rotate(angle));
	helm = angle;
}

void sweepHelm(int angle, int dps=180) {
	int diff = angle - helm;  // distance of travel is given by old and new angles
	// int dps = 180;  // angular velocity in degrees per second (180: -45 to 45 in half second)
	int inc = 2;  // optimal increment: 2 degrees
	if (diff < 0)
		inc = 0 - inc;
	int pause = 10;  // optimal pause: 10 ms
	int ttime = (int)(diff * 1000) / dps; // travel time varies with distance and velocity 
	ttime = abs(ttime);
	int steps = (int)ttime / pause;
	logger(50, "angle:%d, helm:%d, ttime:%d, steps:%d", angle, helm, ttime, steps);

	int n = helm;
	for (int i=0; i<steps; i++) {
		n += inc;
		jerkHelm(n);
		delay(pause);
	}
	jerkHelm(angle); // remainder
}

void jerkThrottle(int angle) {
	servoThrottle.write(rotate(angle));
	throttle = angle;
}

void sweepThrottle(int angle, int dps=180) {
	int diff = angle - throttle;  // distance of travel is given by old and new angles
	// int dps = 180;  // angular velocity in degrees per second (180: -45 to 45 in half second)
	int inc = 2;  // optimal increment: 2 degrees
	if (diff < 0)
		inc = 0 - inc;
	int pause = 10;  // optimal pause: 10 ms
	int ttime = (int)(diff * 1000) / dps; // travel time varies with distance and velocity 
	ttime = abs(ttime);
	int steps = (int)ttime / pause;
	logger(50, "angle:%d, throttle:%d, ttime:%d, steps:%d", angle, throttle, ttime, steps);

	int n = throttle;
	for (int i=0; i<steps; i++) {
		n += inc;
		jerkThrottle(n);
		delay(pause);
	}
	jerkThrottle(angle); // remainder
}

void warmup() {
	logger(100, "warmup");
	sweepHelm( 20); delay(300);
	sweepHelm(-20); delay(300);
	sweepHelm(  0); delay(300);
	sweepThrottle( 20); delay(300);
	sweepThrottle(-20); delay(300);
	sweepThrottle(  0); delay(300);
}

void testSweepHelm() {
	logger(100, "test sweep helm");
	sweepHelm( 0); delay(300);
	sweepHelm( 45); delay(300);
	sweepHelm(-45); delay(300);
	sweepHelm( 45); delay(300);
	sweepHelm(-45); delay(300);
	sweepHelm( 45); delay(300);
	sweepHelm(-45); delay(300);
	sweepHelm(  0);
}

void testJerkHelm() {
	logger(100, "test jerk helm");
	jerkHelm( 0); delay(300);
	jerkHelm( 45); delay(300);
	jerkHelm(-45); delay(300);
	jerkHelm( 45); delay(300);
	jerkHelm(-45); delay(300);
	jerkHelm( 45); delay(300);
	jerkHelm(-45); delay(300);
	jerkHelm( 0);
}

void testSweepThrottle() {
	logger(100, "test sweep throttle");
	sweepThrottle( 0); delay(300);
	sweepThrottle( 45); delay(300);
	sweepThrottle(-45); delay(300);
	sweepThrottle( 45); delay(300);
	sweepThrottle(-45); delay(300);
	sweepThrottle( 45); delay(300);
	sweepThrottle(-45); delay(300);
	sweepThrottle(  0);
}

void testJerkThrottle() {
	logger(100, "test jerk throttle");
	jerkThrottle( 0); delay(300);
	jerkThrottle( 45); delay(300);
	jerkThrottle(-45); delay(300);
	jerkThrottle( 45); delay(300);
	jerkThrottle(-45); delay(300);
	jerkThrottle( 45); delay(300);
	jerkThrottle(-45); delay(300);
	jerkThrottle(  0);
}

void setup() {
	// setup logging via serial monitor
	logging = false;
	Serial.begin(115200);
	for (int i=0; i<25; i++) {
		if (Serial) {
			logging = true;
			Serial.setTimeout(100);
		}
		delay(500);
	}
	logger(100, "\nbegin setup");

	// setup servos  (attach always returns 1)
	servoHelm.attach(6);
	servoThrottle.attach(9);

	// set initial position (doesn't work, read returns ~9000)
	//helm = unrotate(servoHelm.read());
	//throttle = unrotate(servoThrottle.read());
	//logger(50, "start position helm:%d, throttle:%d", helm, throttle);
	//if (helm != 0)
	//	jerkHelm(0);
	//if (throttle != 0)
	//	jerkThrottle(0);

	warmup();
	//testSweepHelm();
	//testJerkHelm();
	//testSweepThrottle();
	//testJerkThrottle();

	logger(100, "setup complete");
}



void loop() {
	delay(1000);
}

