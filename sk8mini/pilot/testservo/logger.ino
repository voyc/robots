/* 
logger.ino
log to serial port 
example:
logger(100, "begin setup");
*/

boolean logging = false;  // set true if Serial connected
int loglevel = 100;  // set by programmer
void logger(int level, char* msg, ...) {
	if (logging && (level >= loglevel)) {
		char buffer[160];
		va_list va;
		va_start (va, msg);
		vsprintf (buffer, msg, va);
		va_end (va);
		Serial.println(buffer);
	}
}

void setupLogger() {
	logging = false;
	Serial.begin(115200);
	for (int i=0; i<25; i++) {
		if (Serial) {
			logging = true;
			Serial.setTimeout(100);
		}
		delay(500);
	}
}

