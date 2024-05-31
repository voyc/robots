/*
sk8mini.h - shared globals
*/


/*---- espnow globals ----*/

uint8_t gcsMacAddr[]   = {0xE0, 0x5A, 0x1B, 0x59, 0x27, 0x74};  // Adafruit Huzzah Feather
uint8_t sk8MacAddr[]   = {0x34, 0x85, 0x18, 0x7B, 0x1D, 0x88};  // Arduino Nano ESP32
uint8_t awacsMacAddr[] = {0x48, 0xE7, 0x29, 0x9E, 0xA3, 0x54};  // ESP32-CAM

int HELM	= 1;
int THROTTLE	= 2;

typedef struct COMMAND {
	int	cmd;
	int	val;
} COMMAND;

typedef struct AHRS {
	float heading;
	float roll;
	float pitch;
	uint8_t sys;
	uint8_t gyro;
	uint8_t accel;
	uint8_t mag;
} AHRS;
