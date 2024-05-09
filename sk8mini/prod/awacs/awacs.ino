/*
awacs.ino - airborne warning and control system

resides on a ESP32-CAM on the awacs drone

Arduino IDE Tools settings
	Board: ESP32 Dev Module
	PSRAM: Enabled
	Programmer: Esptool

function:
	take overhead photos and send to gcs

implementation:
	using CameraWebServer arduino example provided by AI Thinker
	start wifi access point named AWACS, connect laptop to that 
	use http.../capture url from gcs.py

http has delays. other options: 
	do object detection on the awacs and send only object points
		efficient and fast, but we need the photo on the gcs anyway,
		to save for neural net training and for replay in development
	replace http with espnow and serial comm: even slower than http
	use high-bandwidth radio like fpv drones use
		could work, but how does the radio connect to the laptop?

crop on the esp32 - requires conversion from jpeg to bmp to jpeg, too slow
https://stackoverflow.com/questions/67648210/how-do-i-crop-a-bitmap-image-on-an-esp32-cam

CameraWebServer example
./webapps/robots/robots/sk8mini/awacs/example/CameraWebServer - modified, works on awacs

send image via espnow, youtube
https://github.com/talofer99/ESP32CAM-Capture-and-send-image-over-esp-now/blob/master/Camera/Camera.ino

esp_camera source
https://github.com/espressif/esp32-camera/tree/master/driver/include/esp_camera.h
https://github.com/espressif/esp32-camera/tree/master/driver/esp_camera.c
*/

#include "esp_camera.h"
#include <WiFi.h>

//
// WARNING!!! PSRAM IC required for UXGA resolution and high JPEG quality
//            Ensure ESP32 Wrover Module or other board with PSRAM is selected
//            Partial images will be transmitted if image exceeds buffer size
//
//            You must select partition scheme from the board menu that has at least 3MB APP space.
//            Face Recognition is DISABLED for ESP32 and ESP32-S2, because it takes up from 15 
//            seconds to process single frame. Face Detection is ENABLED if PSRAM is enabled as well

// ===================
// Select camera model
// ===================
//#define CAMERA_MODEL_WROVER_KIT // Has PSRAM
//#define CAMERA_MODEL_ESP_EYE // Has PSRAM
//#define CAMERA_MODEL_ESP32S3_EYE // Has PSRAM
//#define CAMERA_MODEL_M5STACK_PSRAM // Has PSRAM
//#define CAMERA_MODEL_M5STACK_V2_PSRAM // M5Camera version B Has PSRAM
//#define CAMERA_MODEL_M5STACK_WIDE // Has PSRAM
//#define CAMERA_MODEL_M5STACK_ESP32CAM // No PSRAM
//#define CAMERA_MODEL_M5STACK_UNITCAM // No PSRAM
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
//#define CAMERA_MODEL_TTGO_T_JOURNAL // No PSRAM
//#define CAMERA_MODEL_XIAO_ESP32S3 // Has PSRAM
// ** Espressif Internal Boards **
//#define CAMERA_MODEL_ESP32_CAM_BOARD
//#define CAMERA_MODEL_ESP32S2_CAM_BOARD
//#define CAMERA_MODEL_ESP32S3_CAM_LCD
//#define CAMERA_MODEL_DFRobot_FireBeetle2_ESP32S3 // Has PSRAM
//#define CAMERA_MODEL_DFRobot_Romeo_ESP32S3 // Has PSRAM
#include "camera_pins.h"

//#define CONNECT_AS_STATION 
#define CONNECT_AS_ACCESSPOINT 

// ===========================
// Enter your WiFi credentials
// ===========================
const char* ssid = "JASMINE_2G";
const char* password = "8496HAG#1";
const char* ssidAP = "AWACS";
const char* passwordAP = "indecent";
const int channel = 1;
const int numConnections = 4;


void startCameraServer();
void setupLedFlash(int pin);

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG; // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  
  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if(config.pixel_format == PIXFORMAT_JPEG){
    if(psramFound()){
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 32;
  
  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1); // flip it back
    s->set_brightness(s, 1); // up the brightness just a bit
    s->set_saturation(s, -2); // lower the saturation
  }
  // drop down frame size for higher initial frame rate
  if(config.pixel_format == PIXFORMAT_JPEG){
    s->set_framesize(s, FRAMESIZE_QVGA);
  }

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

#if defined(CAMERA_MODEL_ESP32S3_EYE)
  s->set_vflip(s, 1);
#endif

// Setup LED FLash if LED pin is defined in camera_pins.h
#if defined(LED_GPIO_NUM)
  setupLedFlash(LED_GPIO_NUM);
#endif

#if defined(CONNECT_AS_STATION)
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected as station");
  IPAddress IP = WiFi.localIP();
#else
  WiFi.softAP(ssidAP, passwordAP, channel, 0, numConnections);
  Serial.print("WiFi connected as access point ");
  Serial.println(ssidAP);
  IPAddress IP = WiFi.softAPIP();
#endif


/*
this is the unique stuff we have added to the example
*/
  Serial.print(" http://");
  Serial.println(IP);

  // tune settings for sk8mini
  config.frame_size = FRAMESIZE_UXGA;
		// label            res         ratio   quality
		// FRAMESIZE_QVGA   320 x  240            4
		// FRAMESIZE_VGA    640 x  480            4
		// FRAMESIZE_SVGA   800 x  600            4
		// FRAMESIZE_HD    1280 x  720  16:9     10
		// FRAMESIZE_SXGA  1280 x 1024   4:3
		// FRAMESIZE_UXGA  1600 x 1200   5:4     10
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY; //CAMERA_GRAB_LATEST
  config.jpeg_quality = 12;  // 4 to 63, lower is better

  startCameraServer();
  Serial.println("web server started");
}

void loop() {
  // Do nothing. Everything is done in another task by the web server
  delay(10000);
}
