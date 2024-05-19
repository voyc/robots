/* 
pilot.ino  
for Arduino ESP32 on sk8mini
implement webserver and services to allow remote user to pilot the sk8 via http

uploading to ESP32
give me permission to write to DFU port
echo 'SUBSYSTEMS=="usb", ATTRS{idVendor}=="2341", MODE:="0666"' | sudo tee /etc/udev/rules.d/60-arduino-esp32.rules && sudo udevadm trigger && sudo udevadm control --reload-rules
from https://forum.arduino.cc/t/arduino-nano-esp32-esptool-error-argument-baud-b-invalid-arg-auto-int-value-upload-speed/1152185/5

example using webserver:
/home/john/Arduino/libraries/ESPAsyncWebServer-master/src/WebRequest.cpp 
*/

#include <WiFi.h>
#include "ESPAsyncWebServer.h"
#include <ESP32Servo.h>

/*
*
* logging
*
*/
boolean logging = false;  // set true if Serial connected
int loglevel = 100;  // set by programmer
void logger(int level, char* msg, ...) {
	if (logging && (level >= loglevel)) {
		char buffer[160];
		va_list va;
		va_start (va, msg);
		vsprintf (buffer, msg, va);
		va_end (va);
		Serial.println(buffer);
	}
}

void setupLogger() {
	logging = false;
	Serial.begin(115200);
	for (int i=0; i<25; i++) {
		if (Serial) {
			logging = true;
			Serial.setTimeout(100);
		}
		delay(500);
	}
}

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

	int travel = angle - helm; // travel vector (distance) given by old and new angles
	if (travel < 0)   // let increment match the sign of the travel vector
		inc = 0 - inc;
	int ttime = (int)(abs(travel) * 1000) / dps; // travel time in ms varies with vector and velocity 
	int steps = (int)travel / inc; // vector and increment gives steps, rounded down
	int pause = 0;
	if ((ttime > 0) && (steps > 0))
		pause = (int)ttime / steps; // ttime and steps gives pause for each step, rounded down
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
* wifi and webserver
*
*/

//const char* ssid = "JASMINE_2G"; 
//const char* password = "8496HAG#1";
const char* ssid = "AWACS";
const char* password = "indecent";

AsyncWebServer server(8080);

struct command {
	int dir;
	int dgr;
	char s[140];
};


struct command parseQueryString(AsyncWebServerRequest* request) {
	command cmd;

	AsyncWebParameter* param = request->getParam(0);
	String name = param->name();
	String value = param->value();

	cmd.dgr = value.toInt();

	cmd.dir = 1;
	if (name == "port" || name == "astern")
		cmd.dir = -1;
	else
		cmd.dir = 1;
	//cmd.dir = 0 - cmd.dir;	// ?

	String scmd = request->url();
	scmd = scmd.substring(1);

	sprintf(cmd.s, "%s %s %s", scmd, name, value);

	return cmd;
}

String reqHelm(AsyncWebServerRequest* request) {
	command cmd = parseQueryString(request);
	helmDesired = 0;
	if (cmd.dgr > 0)
		helmDesired = cmd.dgr * cmd.dir;
	sweepHelm(helmDesired);
	return cmd.s;
}

String reqThrottle(AsyncWebServerRequest* request) {
	command cmd = parseQueryString(request);
	throttle = cmd.dgr * cmd.dir;
	sweepThrottle(throttle);
	return cmd.s;
}

void setup() {
	setupLogger();
	logger(100, "\nbegin setup");

	// setup wifi
	WiFi.mode(WIFI_STA);
	WiFi.begin(ssid, password);
	logger(100, "Connecting to wifi...");
	int wstat = -1;
	while(wstat != WL_CONNECTED) { 
		delay(500);
		wstat = WiFi.status();   // 3:connected
		logger(100, "%d", wstat);
	}
	logger(100, "Connected to WiFi network with IP Address: %s", WiFi.localIP().toString());
	logger(100, "Signal strength: %d", WiFi.RSSI());

	// setup webserver
	server.on("/helm", HTTP_GET, [](AsyncWebServerRequest *request){
		request->send_P(200, "text/plain", reqHelm(request).c_str());
	});
	server.on("/throttle", HTTP_GET, [](AsyncWebServerRequest *request){
		request->send_P(200, "text/plain", reqThrottle(request).c_str());
	});
	server.begin();

	// setup servos
	setupServos();
	warmupServos();
	logger(100, "setup complete");
}



void loop() {
}

