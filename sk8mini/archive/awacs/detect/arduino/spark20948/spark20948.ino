/****************************************************************

spark20948.ino

taken from 
 * Example1_Basics.ino
 * ICM 20948 Arduino Library Demo
 * Use the default configuration to stream 9-axis IMU data
 * Owen Lyke @ SparkFun Electronics
 * Original Creation Date: April 17 2019
 *
 * Please see License.md for the license information.
 *
 * Distributed as-is; no warranty is given.
 ***************************************************************/

/*
SCL  A5
SDA  A4

We don’t need pull-up resistors on the SDA and SCL lines, because they’re built into the Arduino’s I2C pins already.

Input power on this board should be between 1.8-5.5V.

/home/john/Arduino/libraries/SparkFun_9DoF_IMU_Breakout_-_ICM_20948_-_Arduino_Library/src/ICM_20948.cpp
*/

#include "ICM_20948.h" // Click here to get the library: http://librarymanager/All#SparkFun_ICM_20948_IMU

#define SERIAL_PORT Serial

#define WIRE_PORT Wire // Your desired Wire port.			Used when "USE_SPI" is not defined
// The value of the last bit of the I2C address.
// On the SparkFun 9DoF IMU breakout the default is 1, and when the ADR jumper is closed the value becomes 0
#define AD0_VAL 1

ICM_20948_I2C myICM; // Otherwise create an ICM_20948_I2C object

void setup()
{

	SERIAL_PORT.begin(115200);
	while (!SERIAL_PORT)
	{
	};

	WIRE_PORT.begin();
	WIRE_PORT.setClock(400000);

	//myICM.enableDebugging(); // Uncomment this line to enable helpful debug messages on Serial

	bool initialized = false;
	while (!initialized)
	{

		myICM.begin(WIRE_PORT, AD0_VAL);

		//SERIAL_PORT.print(F("Initialization of the sensor returned: "));
		//SERIAL_PORT.println(myICM.statusString());
		if (myICM.status != ICM_20948_Stat_Ok)
		{
			//SERIAL_PORT.println("Trying again...");
			delay(500);
		}
		else
		{
			initialized = true;
		}
	}
}

void loop()
{

	if (myICM.dataReady())
	{
		myICM.getAGMT();				 // The values are only updated when you call 'getAGMT'
		printRaw( myICM.agmt );		 // Uncomment this to see the raw values, taken directly from the agmt structure
		//printRawAGMT( myICM.agmt );		 // Uncomment this to see the raw values, taken directly from the agmt structure
		//printScaledAGMT(&myICM); // This function takes into account the scale settings from when the measurement was made to calculate the values with units
		delay(200);  //30);
	}
	else
	{
		//SERIAL_PORT.println("Waiting for data");
		delay(500);
	}
}

// Below here are some helper functions to print the data nicely!

void printPaddedInt16b(int16_t val)
{
	if (val > 0)
	{
		SERIAL_PORT.print(" ");
		if (val < 10000)
		{
			SERIAL_PORT.print("0");
		}
		if (val < 1000)
		{
			SERIAL_PORT.print("0");
		}
		if (val < 100)
		{
			SERIAL_PORT.print("0");
		}
		if (val < 10)
		{
			SERIAL_PORT.print("0");
		}
	}
	else
	{
		SERIAL_PORT.print("-");
		if (abs(val) < 10000)
		{
			SERIAL_PORT.print("0");
		}
		if (abs(val) < 1000)
		{
			SERIAL_PORT.print("0");
		}
		if (abs(val) < 100)
		{
			SERIAL_PORT.print("0");
		}
		if (abs(val) < 10)
		{
			SERIAL_PORT.print("0");
		}
	}
	SERIAL_PORT.print(abs(val));
}

void printRawAGMT(ICM_20948_AGMT_t agmt)
{
	SERIAL_PORT.print("~Raw   ~");
	printPaddedInt16b(agmt.acc.axes.x);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.acc.axes.y);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.acc.axes.z);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.gyr.axes.x);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.gyr.axes.y);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.gyr.axes.z);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.mag.axes.x);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.mag.axes.y);
	SERIAL_PORT.print("~");
	printPaddedInt16b(agmt.mag.axes.z);
	SERIAL_PORT.println();
}

void printRaw(ICM_20948_AGMT_t agmt) {
	SERIAL_PORT.print("Raw");
	SERIAL_PORT.print(agmt.acc.axes.x);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.acc.axes.y);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.acc.axes.z);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.gyr.axes.x);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.gyr.axes.y);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.gyr.axes.z);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.mag.axes.x);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.mag.axes.y);
	SERIAL_PORT.print("\t");
	SERIAL_PORT.print(agmt.mag.axes.z);
	SERIAL_PORT.println();
}

void printFormattedFloat(float val, uint8_t leading, uint8_t decimals)
{
	float aval = abs(val);
	if (val < 0)
	{
		SERIAL_PORT.print("-");
	}
	else
	{
		SERIAL_PORT.print(" ");
	}
	for (uint8_t indi = 0; indi < leading; indi++)
	{
		uint32_t tenpow = 0;
		if (indi < (leading - 1))
		{
			tenpow = 1;
		}
		for (uint8_t c = 0; c < (leading - 1 - indi); c++)
		{
			tenpow *= 10;
		}
		if (aval < tenpow)
		{
			SERIAL_PORT.print("0");
		}
		else
		{
			break;
		}
	}
	if (val < 0)
	{
		SERIAL_PORT.print(-val, decimals);
	}
	else
	{
		SERIAL_PORT.print(val, decimals);
	}
}

#ifdef USE_SPI
void printScaledAGMT(ICM_20948_SPI *sensor)
{
#else
void printScaledAGMT(ICM_20948_I2C *sensor)
{
#endif
	SERIAL_PORT.print("~Scaled~");
	printFormattedFloat(sensor->accX(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->accY(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->accZ(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->gyrX(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->gyrY(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->gyrZ(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->magX(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->magY(), 5, 2);
	SERIAL_PORT.print("~");
	printFormattedFloat(sensor->magZ(), 5, 2);
	SERIAL_PORT.println();
}
