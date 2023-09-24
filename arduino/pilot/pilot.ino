/* pilot.ino  for Arduino ESP32 on sk8 implement webserver and services to allow remote user to pilot the sk8 
uploading to ESP32
give me permission to write to DFU port
echo 'SUBSYSTEMS=="usb", ATTRS{idVendor}=="2341", MODE:="0666"' | sudo tee /etc/udev/rules.d/60-arduino-esp32.rules && sudo udevadm trigger && sudo udevadm control --reload-rules
from https://forum.arduino.cc/t/arduino-nano-esp32-esptool-error-argument-baud-b-invalid-arg-auto-int-value-upload-speed/1152185/5

/home/john/Arduino/libraries/ESPAsyncWebServer-master/src/WebRequest.cpp 
*/

#include <WiFi.h>
#include "ESPAsyncWebServer.h"
#include <ESP32Servo.h>

const char* ssid = "JASMINE_2G"; 
const char* password = "8496HAG#1";

int helm = 0;
int pinHelm = 9;  // D6
Servo servoHelm;

int throttle = 0;
int pinThrottle = 6; // D3
Servo servoThrottle;

char buffer[40];

AsyncWebServer server(8080);

struct command {
	int dir;
	int dgr;
	char s[40];
};

command parseQueryString(AsyncWebServerRequest* request) {
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

	String scmd = request->url();
	scmd = scmd.substring(1);

	sprintf(cmd.s, "%s %s %s", scmd, name, value);

	return cmd;
}

String setHelm(AsyncWebServerRequest* request) {
	command cmd = parseQueryString(request);
	helm = cmd.dgr * cmd.dir;

	servoHelm.write(servoValue(helm));

	sprintf(buffer, "%s; helm %d throttle %d", cmd.s, helm, throttle);
	Serial.println(buffer);
	return buffer;
}

String setThrottle(AsyncWebServerRequest* request) {
	command cmd = parseQueryString(request);
	throttle = cmd.dgr * cmd.dir;

	servoThrottle.write(servoValue(throttle));

	sprintf(buffer, "%s; helm %d throttle %d", cmd.s, helm, throttle);
	Serial.println(buffer);
	return buffer;
}

int servoValue(int dgr) {
	return dgr + 90;
}
 
void setup() {
	Serial.begin(115200);
	while(!Serial);
	Serial.setTimeout(100);
	Serial.println("\nsetup");

	// setup wifi

	WiFi.begin(ssid, password);
	Serial.print("Connecting");
	int wstat = WiFi.status();
	while(wstat != WL_CONNECTED) { 
		Serial.print(wstat);
		delay(500);
		wstat = WiFi.status();
	}
	Serial.println("");
	Serial.print("Connected to WiFi network with IP Address: ");
	Serial.println(WiFi.localIP());

	server.on("/helm", HTTP_GET, [](AsyncWebServerRequest *request){
		request->send_P(200, "text/plain", setHelm(request).c_str());
	});

	server.on("/throttle", HTTP_GET, [](AsyncWebServerRequest *request){
		request->send_P(200, "text/plain", setThrottle(request).c_str());
	});

	server.begin();

	// setup servos

	servoHelm.attach(pinHelm);
	servoHelm.write(servoValue(helm));

	servoThrottle.attach(pinThrottle);
	servoThrottle.write(servoValue(throttle));
}



void loop() {
	delay(1000);
}


