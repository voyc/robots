/* 
sk8.ino

listen for serial commands from sk8.py 

drive two servers:
	one continuous for drive propulsion
	one 180 for steering

Source.  This sample program has a python program and an Arduino program that talk to each other.
https://projecthub.arduino.cc/projecthub/ansh2919/serial-communication-between-python-and-arduino-e7cce0

This page is the language reference for the Serial object.
https://www.arduino.cc/reference/en/language/functions/communication/serial/

I can use either the sk8.py program or the serial monitor, but not both.

Serial timeout must be 100 for typing into the serial monitor, but can be smaller for sk8.py.
*/  

#include <Servo.h>

bool debug = false;

Servo driveServo;
int driveServoPin = 9;
int driveServoAngle = 90;   // 0 to 180  ??

Servo steerServo;
int steerServoPin = 6;
int steerServoAngle = 90;   // 0 to 180

void setup() {
	Serial.begin(115200);
	Serial.setTimeout(100);
	//Serial.println("");
	//Serial.println("begin");
	if (debug) Serial.println("begin setup");

	driveServo.attach(driveServoPin);
	steerServo.attach(steerServoPin);

	if (debug) Serial.println("setup complete");
}

void loop() {
	if (debug) Serial.println("begin loop");

	while (!Serial.available());
	String input = Serial.readString();
	int pos = input.indexOf(' ');
	String cmd = input.substring(0,pos);
	String sval = input.substring(pos+1);
	int val = sval.toInt();

	if (cmd == "speed") {
		driveServo.write(val);
		delay(15);
		Serial.println("speed " + String(val));
	}
	else if (cmd == "heading") {
		steerServo.write(val);
		delay(15);
		Serial.println("heading " + String(val));
	}
	else {
		Serial.println("command unknown");
	}

	if (debug) Serial.println("loop complete");
}




/* Sweep
 by BARRAGAN <http://barraganstudio.com>
 This example code is in the public domain.

 modified 8 Nov 2013
 by Scott Fitzgerald
 http://www.arduino.cc/en/Tutorial/Sweep
*/


void sweepLoop() {
	for (steerServoAngle = 0; steerServoAngle <= 180; steerServoAngle += 1) {
		// in steps of 1 degree
		steerServo.write(steerServoAngle);
		delay(15);
	}
	for (steerServoAngle = 180; steerServoAngle >= 0; steerServoAngle -= 1) {
		steerServo.write(steerServoAngle);
		delay(15);
	}
}
