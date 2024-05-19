/* 
lcd.ino
*/

#include <LiquidCrystal.h>

const int rs = 12, en = 11, d4 = 5, d5 = 4, d6 = 3, d7 = 2;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);

//MPU9250 IMU(Wire, 0x68);
MPU9250 mpu;

int gx = 0;

void setup() {
	Serial.begin(115200);
	lcd.begin(16,2);	// cols, rows
	lcd.println("lcd started");
}

void loop() {
	lcd.setCursor(0,1);
	lcd.print(millis() / 1000);
	lcd.print(": ");
	lcd.print(gx);

	Serial.print(millis() / 1000);
	Serial.print("\t");
	Serial.println(gx);

	delay(1000);
}
