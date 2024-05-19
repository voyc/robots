/* 
https://projecthub.arduino.cc/ansh2919/serial-communication-between-python-and-arduino-663756
*/

int x;

void setup() {
	Serial.begin(115200);
	Serial.setTimeout(1);
}

void	loop() {
	while (!Serial.available());
	x = Serial.readString().toInt();
	//Serial.print(x + 1);

	int w = x+1;
	float y = x*2.5;
	float z = 4238.15;

	//Serial.print("257\t2406\t927438\n");
	Serial.print(w);
	Serial.print("\t");
	Serial.print(y);
	Serial.print("\t");
	Serial.print(z);
	Serial.println();
}

