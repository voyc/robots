/*
awacs-espnow.ino

resides on a ESP32-CAM on the awacs drone
Arduino IDE Tools settings
	Board: ESP32 Dev Module
	PSRAM: Enabled
	Programmer: Esptool

receive centerpoint from gcs
read photo from camera
crop to 600x600
send to gcs

see gcs.ino for more

architecture options:
1. detect objects on the gcs in python
	a. this is required for now because we need to capture the images for neural net training
	b. comm options:
		i. for now we use the http with the CamWebServer code
		ii. send image thru espnow/serial to python gcs - too slow!
		iii. high-bandwidth radio
2. detect objects here on the awacs
	a. write c++ opencv code for esp32cam
	b. install python and opencv on the esp32cam
	c. run python object detection on a raspberry pi mounted on sk8 vehicle
		i. get image from esp32cam to raspberry pi
		ii. use a camera on the raspberry pi
	
600x600
left, top
cropped x,y

// send image via espnow, youtube
https://github.com/talofer99/ESP32CAM-Capture-and-send-image-over-esp-now/blob/master/Camera/Camera.ino

// CameraWebServer
Arduino IDE->Examples->ESP32->Camera->CameraWebServer
./webapps/robots/robots/sk8mini/awacs/example/CameraWebServer - modified, works on awacs
./webapps/robots/robots/sk8mini/awacs/example/CameraWebServer/CameraWebServer.ino
./.arduino15/packages/esp32/hardware/esp32/2.0.13/libraries/ESP32/examples/Camera/CameraWebServer
./.arduino15/packages/esp32/hardware/esp32/2.0.13/libraries/ESP32/examples/Camera/CameraWebServer/CameraWebServer.ino
./.arduino15/packages/arduino/hardware/esp32/2.0.13/libraries/ESP32/examples/Camera/CameraWebServer
./.arduino15/packages/arduino/hardware/esp32/2.0.13/libraries/ESP32/examples/Camera/CameraWebServer/CameraWebServer.ino

// esp_camera source
https://github.com/espressif/esp32-camera/tree/master/driver/include/esp_camera.h
https://github.com/espressif/esp32-camera/tree/master/driver/esp_camera.c

from esp_camera.h
//	typedef struct {
//	    uint8_t * buf;              // Pointer to the pixel data
//	    size_t len;                 // Length of the buffer in bytes
//	    size_t width;               // Width of the buffer in pixels
//	    size_t height;              // Height of the buffer in pixels
//	    pixformat_t format;         // Format of the pixel data
//	    struct timeval timestamp;   // Timestamp since boot of the first DMA buffer of the frame
//	} camera_fb_t;

*/

#include <WiFi.h>
#include <esp_now.h>
#include <esp_camera.h>
 
// espnow
uint8_t gcsMacAddr[]   = {0xE0, 0x5A, 0x1B, 0x59, 0x27, 0x74};
uint8_t awacsMacAddr[] = {0x48, 0xE7, 0x29, 0x9E, 0xA3, 0x54};

// onetime memory allocation
esp_now_peer_info_t peerInfo;

// camera
#define BOARD_ESP32CAM_AITHINKER
#define CAM_PIN_PWDN 32
#define CAM_PIN_RESET -1 //software reset will be performed
#define CAM_PIN_XCLK 0
#define CAM_PIN_SIOD 26
#define CAM_PIN_SIOC 27
#define CAM_PIN_D7 35
#define CAM_PIN_D6 34
#define CAM_PIN_D5 39
#define CAM_PIN_D4 36
#define CAM_PIN_D3 21
#define CAM_PIN_D2 19
#define CAM_PIN_D1 18
#define CAM_PIN_D0 5
#define CAM_PIN_VSYNC 25
#define CAM_PIN_HREF 23
#define CAM_PIN_PCLK 22
#define LED_BUILTIN 4

static camera_config_t camera_example_config = {
	.pin_pwdn       = CAM_PIN_PWDN,
	.pin_reset      = CAM_PIN_RESET,
	.pin_xclk       = CAM_PIN_XCLK,
	.pin_sccb_sda   = CAM_PIN_SIOD,
	.pin_sccb_scl   = CAM_PIN_SIOC,
	.pin_d7         = CAM_PIN_D7,
	.pin_d6         = CAM_PIN_D6,
	.pin_d5         = CAM_PIN_D5,
	.pin_d4         = CAM_PIN_D4,
	.pin_d3         = CAM_PIN_D3,
	.pin_d2         = CAM_PIN_D2,
	.pin_d1         = CAM_PIN_D1,
	.pin_d0         = CAM_PIN_D0,
	.pin_vsync      = CAM_PIN_VSYNC,
	.pin_href       = CAM_PIN_HREF,
	.pin_pclk       = CAM_PIN_PCLK,
	
	.xclk_freq_hz   = 20000000,
	.ledc_timer     = LEDC_TIMER_0,
	.ledc_channel   = LEDC_CHANNEL_0,
	.pixel_format   = PIXFORMAT_JPEG,
  	.frame_size     = FRAMESIZE_UXGA,
	.jpeg_quality   = 12,
	.fb_count       = 2,
	.grab_mode      = CAMERA_GRAB_WHEN_EMPTY
//	.fb_location    = CAMERA_FB_IN_PSRAM
};

// global variables
boolean running = false;
int numFrame = 0;
int numPacket = 0;
int onSent = 0;

// global constants for cropping and packeting
int bytesPerPixel = 3;
int packetSize = 200;   // espnow max 256
int outputWidth  = 600 * bytesPerPixel;
int outputHeight = 600 * bytesPerPixel;
int inputWidth = 1600 * bytesPerPixel;    // fb->width
int inputHeight = 1200 * bytesPerPixel;   // fp->height
int xCtr = int(inputWidth / 2) * bytesPerPixel;
int yCtr = int(inputHeight / 2) * bytesPerPixel;
int xStart = xCtr - (outputWidth / 2);
int yStart = yCtr - (outputHeight / 2);
int numCols = outputWidth / packetSize;
int numRows = outputHeight / packetSize;

// UI output
void blink(int code, String msg) {
	if (msg.length() > 0) {
		Serial.println(msg);	// for debugging only
	}
	if (code < 0) {  // negative codes are preceded by a long blink
		digitalWrite(LED_BUILTIN, HIGH);   // turn the LED on (HIGH is the voltage level)
		delay(1000);
		digitalWrite(LED_BUILTIN, LOW);    // turn the LED off by making the voltage LOW
		delay(100);
		code = abs(code);
	}
	for (int n=1; n<=code; n++) {
		digitalWrite(LED_BUILTIN, HIGH);  // short blinkes to signal the code
		delay(100);
		digitalWrite(LED_BUILTIN, LOW);
		delay(100);
	}
	delay(100);
}

// callback
void onDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
	// why would anyone use this?
	// no print or delay in here
	if (status != ESP_NOW_SEND_SUCCESS) {
		onSent = -1;
	}
}

void setup() {
	pinMode(LED_BUILTIN, OUTPUT);

	Serial.begin(115200);
	Serial.println("awacs serial started");

	WiFi.mode(WIFI_STA);
	Serial.println("awacs wifi station started");
	
	if (esp_now_init() != 0) {
		blink(-5, "awacs error initializing ESP-NOW");
		return;
	}
	Serial.println("awacs esp-now started");

	esp_now_register_send_cb(onDataSent);
	Serial.println("awacs send callback registered");

	// add peer
	memcpy(peerInfo.peer_addr, gcsMacAddr, 6);
	peerInfo.channel = 0;  
	peerInfo.encrypt = false;
	if (esp_now_add_peer(&peerInfo) != ESP_OK){
		blink(-6, "awacs Failed to add peer");
		return;
	}
	Serial.println("awacs peer added");

	if (esp_camera_init(&camera_example_config) != ESP_OK) {
		blink(-7, "awacs camera init failed");
		return;
	}
	Serial.println("awacs camera init");

	Serial.println("awacs setup complete");
	blink(2, "setup successful");
	running = true;
}

void sendPacket(uint8_t* packetAddr) {
	// Send data to gcs via ESP-NOW
	onSent = 0;
	esp_err_t result = esp_now_send(gcsMacAddr, packetAddr, packetSize);
	 
	if (result != ESP_OK) {
		blink(-2, "awacs send error");
	}
	if (onSent != 0) {
		blink(-3, "awacs onsent error");
	}
	String msg = "awacs packet sent ";
	msg += numPacket;
	Serial.println(msg);
	Serial.println("awacs packet sent");
}

void sendFrame(camera_fb_t* fb) {
	numFrame++;
	Serial.print("awacs sending frame ");
	Serial.print(numFrame);
	Serial.print(", ");
	Serial.print(fb->width);
	Serial.print(", ");
	Serial.print(fb->height);
	Serial.print(", ");
	Serial.print(fb->format);
	Serial.print(", ");
	Serial.print(fb->len);
	Serial.println();

	// break into packets and send each
	uint8_t* packetAddr;
	int x = 0;
	int y = yStart;
	for (int row=0; row<numRows; row++) {
		x = xStart;
		for (int col=0; col<numCols; col++) {
			packetAddr = fb->buf + (y * inputWidth) + x;
			sendPacket( packetAddr);
			x += packetSize;
			String msg = "awacs packet sent ";
			numPacket++;
			msg += numPacket;
			Serial.println(msg);
		}
		y += 1;
	}
}

camera_fb_t* getFrameFromCamera() {
	// acquire the frame buffer
        camera_fb_t* fb = esp_camera_fb_get();  
        if (!fb) {
		blink(-4, "Frame buffer could not be acquired");
		running = false;
		return NULL;
        }

        //replace this with your own function
        //display_image(fb->width, fb->height, fb->pixformat, fb->buf, fb->len);
	sendFrame(fb);

        //return the frame buffer back to be reused
        esp_camera_fb_return(fb);

        return ESP_OK;
}

void loop() {
	if (running) {
		camera_fb_t* fb = getFrameFromCamera();
	}
}
/*	
	// crop frame and send each chunk
	int xcenter
	int ycenter	


	600 byte row split into 3 pieces 200 bytes each
	600 rows
 
	// Send data to gcs via ESP-NOW
	gOnSent = 0;
	esp_err_t result = esp_now_send(gcsMacAddr, (uint8_t *) &packetAwacs, sizeof(packetAwacs));
	 
	if (result != ESP_OK) {
		blink(-2, "awacs send error");
	}
	if (gOnSent != 0) {
		blink(-3, "awacs onsent error");
	}
	Serial.println("awacs data sent");
	delay(2000);
*/


/* 
for option 2, we would send only object coordinates thru espnow

//typedef struct AWACS {
//	int xdonut;
//	int ydonut;
//} AWACS;
//
//AWACS packetAwacs;

typedef struct DONUT {
	int x;
	int y;
	int hdg;
} DONUT;

typedef struct CONE {
	int x;
	int y;
} CONE;

const int MAXCONES = 20;
CONE points[MAXCONES];	// a single memory allocation upfront
int numCones = 9;	// a dynamic usable subset

DONUT donut;
*/

