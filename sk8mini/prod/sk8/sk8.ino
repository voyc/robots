/*
sk8.ino - sk8 controller

runs on sk8 on arduino nano esp32

setup IDE
	port: /dev/ttyACM0
	board: ESP32 Arduino (Arduino) -> Arduino Nano ESP32
	Pin Numbering: By Arduino pin (default)

functions:
	connect to gcscomm via ESP-NOW
	receive pilot commands from gcscomm
	execute pilot commands: helm and throttle
	send roll, pitch, heading to gcscomm via espnow
*/

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);
#define BNO055_SAMPLERATE_DELAY_MS (100)

typedef struct SK8 {
	float heading;
	float roll;
	float pitch;
	uint8_t sys;
	uint8_t gyro;
	uint8_t accel;
	uint8_t  mag;
} SK8;

SK8 packetSk8;

//void onEspnowRcvd(const uint8_t * mac, const uint8_t *incomingData, int len) {
//	//  incoming data into the struct
//	memcpy(&packetSk8, incomingData, sizeof(packetSk8));
//  
//	// send to laptop as string
//	Serial.print(packetSk8.roll);
//	Serial.print("\t");
//	Serial.print(packetSk8.pitch);
//	Serial.print("\t");
//	Serial.println(packetSk8.heading);
//}
// 
//void onEspnowSent(const uint8_t * mac, const uint8_t *incomingData, int len) {
//	// move incoming data into the struct
//	memcpy(&packetSk8, incomingData, sizeof(packetSk8));
//  
//	// send to laptop as string
//	Serial.print(packetSk8.roll);
//	Serial.print("\t");
//	Serial.print(packetSk8.pitch);
//	Serial.print("\t");
//	Serial.println(packetSk8.heading);
//}
 
void setup() {
	Serial.begin(115200);
	delay(100);

//	WiFi.mode(WIFI_STA);
//	Serial.println("gcs wifi station started");
//	
//	if (esp_now_init() != 0) {
//		Serial.println("gcs Error initializing ESP-NOW");
//		return;
//	}
//	esp_now_register_recv_cb(onEspnowRcvd);
//	esp_now_register_send_cb(onEspnowSent);
//	Serial.println("gcs esp-now started");

	/* Initialise the sensor */
	if(!bno.begin()) {
	  /* There was a problem detecting the BNO055 ... check your connections */
	  Serial.print("Ooops, no BNO055 detected ... Check your wiring or I2C ADDR!");
	  while(1);
	}

	delay(1000);

	/* Use external crystal for better accuracy */
	bno.setExtCrystalUse(true);
 
	/* Display some basic information on this sensor */
	//displaySensorDetails();


}
 
void readSensor() {
	sensors_event_t event;
	bno.getEvent(&event);

	packetSk8.heading = (float)event.orientation.x;
	packetSk8.roll    = (float)event.orientation.y;
	packetSk8.pitch   = (float)event.orientation.z;

	bno.getCalibration(&packetSk8.sys, &packetSk8.gyro, &packetSk8.accel, &packetSk8.mag);
	
	delay(BNO055_SAMPLERATE_DELAY_MS);
}

	
void loop() {
	delay(100);
	readSensor();

	Serial.print(packetSk8.heading);
	Serial.print(F("\t"));
	Serial.print(packetSk8.roll);
	Serial.print(F("\t"));
	Serial.print(packetSk8.pitch);
	Serial.print(F("\t"));
	Serial.print(packetSk8.sys);
	Serial.print(F("\t"));
	Serial.print(packetSk8.gyro);
	Serial.print(F("\t"));
	Serial.print(packetSk8.accel);
	Serial.print(F("\t"));
	Serial.print(packetSk8.mag);
	Serial.println();

	// send pitch, roll, heading to gcs

	// receive helm and throttle commands from gcs

	// execute helm and throttle commands
}


