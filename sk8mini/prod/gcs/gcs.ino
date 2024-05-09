/*
gcs.ino - ground control station comms dongle

runs on an Arduino Nano ESP32 dongle connected to the laptop

functions:
	receives AHRS data from sensor on the sk8 via ESP-NOW
	passes same data to gcs.py on the laptop via Serial
	receives helm and throttle commands from gcs.py
	passes sam commands to gcs.ino via Serial

setup IDE:


for ESP-NOW see https://dronebotworkshop.com/esp-now/
for laptop-arduino comm: https://projecthub.arduino.cc/ansh2919/serial-communication-between-python-and-arduino-663756
*/

#include <WiFi.h>
#include <esp_now.h>
 
uint8_t gcsMacAddr[]   = {0xE0, 0x5A, 0x1B, 0x59, 0x27, 0x74};  // Arduino Nano ESP32
uint8_t awacsMacAddr[] = {0x48, 0xE7, 0x29, 0x9E, 0xA3, 0x54};  // ESP32-CAM
uint8_t sk8MacAddr[]   = {0x48, 0xE7, 0x29, 0x9E, 0xA3, 0x54};  // ESP32-CAM

typedef struct SK8 {
	float heading;
	float roll;
	float pitch;
} SK8;

SK8   packetSk8;
 
void onEspnowRcvd(const uint8_t * mac, const uint8_t *incomingData, int len) {
	// parse incoming data by moving it into the struct
	memcpy(&packetSk8, incomingData, sizeof(packetSk8));
  
	// send to laptop as string
	Serial.print(packetSk8.roll);
	Serial.print("\t");
	Serial.print(packetSk8.pitch);
	Serial.print("\t");
	Serial.println(packetSk8.heading);
}
 
void setup() {
	Serial.begin(115200);
	Serial.println("gcs serial started");

	WiFi.mode(WIFI_STA);
	Serial.println("gcs wifi station started");
	
	if (esp_now_init() != 0) {
		Serial.println("gcs Error initializing ESP-NOW");
		return;
	}
	esp_now_register_recv_cb(onEspnowRcvd);
	Serial.println("gcs esp-now started");

	packetSk8.roll = 12;
	packetSk8.pitch = 1;
	packetSk8.heading = 32;
}
 
void loop() {
	// send to laptop as string
	Serial.print(packetSk8.roll);
	Serial.print("\t");
	Serial.print(packetSk8.pitch);
	Serial.print("\t");
	Serial.println(packetSk8.heading);
	
	delay(500);
}

