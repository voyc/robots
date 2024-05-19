#include <Servo.h>

Servo servo3;
Servo servo6;
Servo servo9;
Servo servob;

void setup() {
	Serial.begin(9600); //115200);
	Serial.setTimeout(1);
	Serial.println("");
	Serial.println("begin setup");

	servo3.attach(3);
	servo3.write(45);
	int p3 = servo3.read();
	Serial.println("pin 3 says " + String(p3));

	servo6.attach(6);
	servo6.write(45);
	int p6 = servo6.read();
	Serial.println("pin 6 says " + String(p6));

	servo9.attach(9);
	servo9.write(45);
	int p9 = servo9.read();
	Serial.println("pin 9 says " + String(p9));

	servob.attach(11);
	servob.write(45);
	int pb = servob.read();
	Serial.println("pin b says " + String(pb));


	Serial.println("setup complete");
}

int state = 1;
int loopcnt = 0;

void loop() {
	Serial.println("begin loop");

	if (loopcnt < 30) {
		if (state == 1) {	
			servo3.write(45);
			servo6.write(45);
			servo9.write(45);
			servob.write(45);
			state = 2;
		}
		else {
			servo3.write(135);
			servo6.write(135);
			servo9.write(135);
			servob.write(135);
			state = 1;
		}
	}

	loopcnt++;

	delay(1000);

	Serial.println("loop complete");
}


