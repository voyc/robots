/*
gcs.ino - ground control station comms dongle

runs on:
	an Adafruit ESP32 Feather (Huzzah) connected to the laptop as a dongle

functions:
	receives AHRS data from sk8 via espnow
	passes same data to gcs.py on the laptop via Serial
	receives helm and throttle commands from gcs.py via Serial
	passes same commands to sk8 via espnow

setup IDE for download:
	board: Adafruit ESP32 Feather
	port dev/ttyUSB0

NOTE: successful sketch download ends with these messages:
	Leaving...
	Hard resetting via RTS pin...

serial:
	used for downloading a sketch
	used for communicating data between gcs.ino and gcs.py
	Serial Monitor is NOT used

espnow: 
	https://dronebotworkshop.com/esp-now/

laptop-arduino comm: 
	https://projecthub.arduino.cc/ansh2919/serial-communication-between-python-and-arduino-663756

pilot commands: 
	~/webapps/robots/robots/sk8mini/pilot/pilot.ino, pilot.py 
*/

#include <WiFi.h>
#include <esp_now.h>
#include "sk8mini.h"
 
/*---- globals ----*/

AHRS ahrs;
PILOT pilot;
 
/*---- state UI ----*/

int statecode = 0;
#define STATE_SERIAL_READY		1
#define STATE_WIFI_STATION_READY	2
#define STATE_ESPNOW_READY		3
#define STATE_SETUP_COMPLETE		5
#define ERROR_SERIAL_FAILED		-1
#define ERROR_INITIALIZING_ESPNOW	-2
#define ERROR_PILOT_SEND_FAILED		-4
#define ERROR_PILOT_DELIVERY_FAILED	-5
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

/*---- espnow callbacks ----*/

esp_now_peer_info_t peerInfo;

void onPilotSent(const uint8_t* mac, esp_now_send_status_t sentstatus) {
	if (sentstatus != ESP_NOW_SEND_SUCCESS) {
		state(ERROR_PILOT_DELIVERY_FAILED);
	}
}

void onAhrsRcvd(const uint8_t * mac, const uint8_t *incomingData, int len) {
	// parse incoming data by moving it into the struct
	memcpy(&ahrs, incomingData, sizeof(ahrs));
  
	// send to laptop as string
	Serial.print(ahrs.heading);
	Serial.print("\t");
	Serial.print(ahrs.roll);
	Serial.print("\t");
	Serial.print(ahrs.pitch);
	Serial.print("\t");
	Serial.print(ahrs.sys);
	Serial.print("\t");
	Serial.print(ahrs.gyro);
	Serial.print("\t");
	Serial.print(ahrs.accel);
	Serial.print("\t");
	Serial.println(ahrs.mag);
}
 
void setup() {
	pinMode(LED_BUILTIN, OUTPUT);

	Serial.begin(115200);
	delay(100);
	if (!Serial) {
		state(ERROR_SERIAL_FAILED);
		return;
	}
	state(STATE_SERIAL_READY);

	WiFi.mode(WIFI_STA);
	delay(100);
	state(STATE_WIFI_STATION_READY);
	
	if (esp_now_init() != 0) {
		state(ERROR_INITIALIZING_ESPNOW);
		return;
	}
	esp_now_register_recv_cb(onAhrsRcvd);
	esp_now_register_send_cb(onPilotSent);

	// Register peer
	memcpy(peerInfo.peer_addr, sk8MacAddr, 6);
	peerInfo.channel = 0;  
	peerInfo.encrypt = false;
	
	// Add peer        
	if (esp_now_add_peer(&peerInfo) != ESP_OK){
		state(ERROR_ADDING_PEER);
		return;
	}


	state(STATE_ESPNOW_READY);
	state(STATE_SETUP_COMPLETE);
}
 
void getPilot() {  // from laptop and send to sk8
	// read string from serial port
	//int cnt = 1000;
	//while (!Serial.available() && cnt > 0) {
	//	blink(1);
	//	cnt -= 1;
	//}
	if (!Serial.available()) {
		return;
	}

	String s = Serial.readString();
	
	// parse into struct
	char sep = '\t';
	int len = s.length();
	int i = 0;
	for (int i=0; i<len; i++) {
		if (s.charAt(i) == sep) {
			pilot.helm = s.substring(0,i).toInt();
			pilot.throttle = s.substring(i,len).toInt();
		}
	}

	// send struct to sk8 via espnow
 	esp_err_t result = esp_now_send(sk8MacAddr, (uint8_t *) &pilot, sizeof(pilot));
	if (result != ESP_OK) {
		state(ERROR_PILOT_SEND_FAILED);
	}
}

void loop() {
	// signal error condition
	//if (statecode < 0) {
	//	blink(abs(statecode));
	//	delay(1000);
	//	return;
	//}

	getPilot();
}

