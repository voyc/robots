/*
sk8.ino - sk8 controller

runs on sk8 on arduino nano esp32

IDE settings:
	port: /dev/ttyACM0
	board: ESP32 Arduino (Arduino) -> Arduino Nano ESP32
	Pin Numbering: By GPIO Number (legacy)

Serial port:
	used only for downloading a sketch
	sometimes gets "error opening serial port" if the Serial Monitor is open
	pull the jumper before turning battery on

jumper: 
	closed: For standalone operation, the jumper must be closed, to connect the battery to the 3.3V pin.
	open: For serial cable operation, the jumper must be open, because 5V power is already coming in
		via the serial cable, and the 3.3V pin has become an output.

Wiring diagram for the custom Sk8 board:
	~/webapps/robots/robots/sk8mini/perfboard_sk8mini_1.xcf

functions:
	connect to gcscomm via ESP-NOW
	receive pilot commands from gcscomm
	execute pilot commands: helm and throttle
	send roll, pitch, heading to gcscomm via espnow
	manage:
		espnow comm: receive pilot, send ahrs
		servos: helm and throttle
		ahrs sensors:  mag, gyro, accel

Adafruit BNO055:
	The BNO055 I2C does not work well with ESP32 and other chips.
	https://learn.adafruit.com/adafruit-bno055-absolute-orientation-sensor/overview

espnow: 
	https://dronebotworkshop.com/esp-now/

pilot, servos:
	~/webapps/robots/robots/sk8mini/pilot
		pilot.ino - helm and throttle implemented via espwebserver
	
setupServos
warmupServos

setHelm
getHelm
sweepHelm
zeroHelm
checkHelm

setThrottle
getThrottle
sweepThrottle
zeroThrottle
checkThrottle
adjustThrottle

send("start")
send("kill")

send("throttle?stop")
send("throttle?ahead=n")
send("throttle?astern=n")

send("helm?amidships")
send("helm?port=n")
send("helm?starboard=n")
*/

#include <WiFi.h>
#include <Wire.h>
#include <esp_now.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>
#include <ESP32Servo.h>
#include "sk8mini.h"

// explicit function prototype to specify the default value
void setHelm(int angle, boolean isadjust=false);
void setThrottle(int angle, boolean isadjust=false);

/*---- AHRS globals ----*/

#define BNO055_SAMPLERATE_DELAY_MS 10  // 10
Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);
sensors_event_t ahrs_event;

#define heading_threshold  0 //1
#define roll_threshold 0.0   //0.1
PILOT pilot;
boolean pilot_available = false;

AHRS ahrs;
float heading = 9999;
float roll = 9999;
int mag = -1;
int gyro = -1;

/*---- state UI ----*/

int statecode = 0;
#define STATE_WIFI_STATION_READY	2
#define STATE_ESPNOW_READY		3
#define STATE_AHRS_READY		4
#define STATE_SERVOS_READY		5
#define STATE_SETUP_COMPLETE		6
#define ERROR_INITIALIZING_ESPNOW	-2
#define ERROR_BNO055_NOT_DETECTED	-3
#define ERROR_PACKET_SEND_FAILED	-4
#define ERROR_PACKET_DELIVERY_FAILED	-5
#define ERROR_ADDING_PEER		-6

void state(int code) {
	statecode = code;
}

int blinkrate = 3;  // blinks per second
int blinkdelay = int(1000 / (blinkrate * 2)); 

void blink(int num) {
	for (int i=0; i<num; i++) {
		digitalWrite(LED_BUILTIN, HIGH);   // turn the LED on (HIGH is the voltage level)
		delay(blinkdelay);
		digitalWrite(LED_BUILTIN, LOW);    // turn the LED off by making the voltage LOW
		delay(blinkdelay);
	}
	delay(1000);
}


void readAhrs() { // from sensor into struct
	bno.getEvent(&ahrs_event);
	ahrs.heading = (float)ahrs_event.orientation.x;  // heading and pitch, x,z reversed
	ahrs.roll    = (float)ahrs_event.orientation.y;
	ahrs.pitch   = (float)ahrs_event.orientation.z;
	bno.getCalibration(&ahrs.sys, &ahrs.gyro, &ahrs.accel, &ahrs.mag); // gyro, mag reversed
	delay(BNO055_SAMPLERATE_DELAY_MS);
}

void sendAhrs() { // to gcs
 	esp_err_t result = esp_now_send(gcsMacAddr, (uint8_t *) &ahrs, sizeof(ahrs));
	if (result != ESP_OK) {
		state(ERROR_PACKET_SEND_FAILED);
	}
}


/*---- espnow callbacks ----*/

esp_now_peer_info_t peerInfo;

void onEspnowRcvd(const uint8_t* mac, const uint8_t *incomingData, int len) {
	memcpy(&pilot, incomingData, sizeof(pilot));
	pilot_available = true;  // loop will execute
}
 
void onEspnowSent(const uint8_t* mac, esp_now_send_status_t sentstatus) {
	if (sentstatus != ESP_NOW_SEND_SUCCESS) {
		state(ERROR_PACKET_DELIVERY_FAILED);
	}
}

/*---- setup ----*/

void setup() {
	pinMode(LED_BUILTIN, OUTPUT);

	// wifi
	WiFi.mode(WIFI_STA);
	delay(100);
	state(STATE_WIFI_STATION_READY);

	// espnow
	if (esp_now_init() != 0) {
		state(ERROR_INITIALIZING_ESPNOW);
		return;
	}
	esp_now_register_recv_cb(onEspnowRcvd);
	esp_now_register_send_cb(onEspnowSent);
	memcpy(peerInfo.peer_addr, gcsMacAddr, 6);
	peerInfo.channel = 0;  
	peerInfo.encrypt = false;
	if (esp_now_add_peer(&peerInfo) != ESP_OK){
		state(ERROR_ADDING_PEER);
		return;
	}
	state(STATE_ESPNOW_READY);

	// sensor
	if(!bno.begin()) {
		state(ERROR_BNO055_NOT_DETECTED);
		return;
	}
	bno.setExtCrystalUse(true);
	state(STATE_AHRS_READY);

	// servos
	setupServos();
	warmupServos();
	state(STATE_SERVOS_READY);

	state(STATE_SETUP_COMPLETE);
}
 
/*---- loop ----*/ 

// native abs() does not seem to work on ESP32 chips
#ifdef abs
#undef abs
#endif
#define abs(x) ((x)>0 ? (x) : -(x))

void loop() {
	// signal error condition
	if (statecode < 0) {
		blink(abs(statecode));
		delay(1000);
		return;
	}

	// handle incoming pilot commnd
	if (pilot_available) {  // set by espnow callback
		execute();
		pilot_available = false;
	}

	// handle incoming sensor data 
	readAhrs();
	
	// abs() does not seem to work on ESP32 chips
	//float diffHeading =  heading - ahrs.heading;
	//float diffRoll = roll - ahrs.roll;
	//if (diffHeading < 0) diffHeading = 0 - diffHeading;
	//if (diffRoll < 0) diffRoll = 0 - diffRoll;

	//if (diffRoll == abs(roll - ahrs.roll)) {
	//	ahrs.roll = 25;
	//}

	bool isNewHeading = abs(heading - ahrs.heading) > heading_threshold;
	bool isNewRoll = abs(roll - ahrs.roll) > roll_threshold;
	bool isNewMag = abs(mag != ahrs.mag);
	bool isNewGyro = abs(gyro != ahrs.gyro);

	//if (true) {
	if (isNewHeading || isNewRoll || isNewMag || isNewGyro) {
		sendAhrs();
		heading = ahrs.heading;
		roll = ahrs.roll;
		mag  = ahrs.mag;
		gyro = ahrs.gyro;
	}
}

void execute() {
	setHelm(pilot.helm);
	setThrottle(pilot.throttle);
	// int calcThrottleAdjustment(int throttle, int helm) {
}

/*---- servos ----*/

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

// set the value of helm and write it to the servo
void setHelm(int angle, boolean isadjust) {
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

	int travel = angle - helm; // travel vector (distance) given by old and new angles
	if (travel < 0)   // let increment match the sign of the travel vector
		inc = 0 - inc;
	int ttime = (int)(abs(travel) * 1000) / dps; // travel time in ms varies with vector and velocity 
	int steps = (int)travel / inc; // vector and increment gives steps, rounded down
	int pause = 0;
	if ((ttime > 0) && (steps > 0))
		pause = (int)ttime / steps; // ttime and steps gives pause for each step, rounded down
	//logger(50, "sweepHelm dps:%d, angle:%d, helm:%d, ttime:%d, steps:%d, pause:%d", dps, angle, helm, ttime, steps, pause);

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
void setThrottle(int angle, boolean isadjust) {
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
	//logger(50, "sweepThrottle angle:%d, throttle:%d, ttime:%d, steps:%d", angle, throttle, ttime, steps);

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
	//logger(30, "calculate adjusted throttle: %d:%d, helm:%d, factor:%d, adj:%d", throttle, adjusted, helm, factor, adj);
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
	setThrottle( 20); delay(300);
	zeroThrottle();   delay(100);
	setThrottle(-33); delay(300); // note the ratio of forward to backward speeds
	zeroThrottle();
}

