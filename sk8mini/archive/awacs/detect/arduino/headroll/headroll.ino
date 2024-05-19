/* 
headroll.ino

read gyro/accelerometer/magnetometer

display 
	heading: 0:360 degrees compass heading
	roll: -45:+45 degrees roll of deck


MPU9250 - same as MPU6050 + magnetometer
https://arduino.stackexchange.com/questions/20740/how-to-do-run-time-calibration-for-mpu9250

http://www.arduinolearning.com/code/arduino-mpu-9250-example.php

MPU6050 includes Digital Motion Processor (DMP)

libraries
	MPU6050
	I2Cdev
	MPU6050 Motion Apps

ATTITUDE & HEADING REFERENCE SYSTEM (AHRS)
https://www.vectornav.com/resources/inertial-navigation-primer/theory-of-operation/theory-ahrs

Micro-Electromechanical Systems (MEMS)

Calibration
https://wired.chillibasket.com/2015/01/calibrating-mpu6050/

Paul McWhorter: 9-axus IMU
Walks through simplified versions of the math and concepts.
https://toptechboy.com/arduino-based-9-axis-inertial-measurement-unit-imu-based-on-bno055-sensor/
https://www.youtube.com/watch?v=p_qZ-ie2R7o&t=2s



running connection_check
	i2c address is 0x68, which indicates MPU6050
	AK8963 address is 0, magnetometer not found



*/

#include "MPU9250.h"

MPU9250 mpu;

int gx = 0;

void setup() {
	Serial.begin(115200);
	Wire.begin();
	delay(2000);
	Serial.println( "serial and wire initiated");

	if (!mpu.setup(0x68)) {  // change to your own address
		while (1) {
			Serial.println("MPU connection failed. Please check your connection with `connection_check` example.");
			delay(5000);
		}
	}
}

void loop() {
	if (mpu.update()) {
		static uint32_t prev_ms = millis();
		if (millis() > prev_ms + 25) {
			print_roll_pitch_yaw();
			prev_ms = millis();
		}
	}
}

void print_roll_pitch_yaw() {
	Serial.print("Yaw, Pitch, Roll: ");
	Serial.print(mpu.getYaw(), 2);
	Serial.print(", ");
	Serial.print(mpu.getPitch(), 2);
	Serial.print(", ");
	Serial.println(mpu.getRoll(), 2);
}
