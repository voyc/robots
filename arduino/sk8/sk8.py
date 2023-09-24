''' 
sk8.py
communicate with arduino to manage servo motor

see companion Arduino program: serialserver.ino

Source.  This sample program has a python program and an Arduino program that talk to each other.
https://create.arduino.cc/projecthub/ansh2919/serial-communication-between-python-and-arduino-e7cce0


input number must be angle between 0 and 180

find port name
python3 -m serial.tools.list_ports
or
from serial.tools import list_ports
list_ports.comports()  # Outputs list of available serial ports

'''  
import serial # this is the pyserial library
import time

arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=.1)

def write_read(x):
	arduino.write(bytes(x, 'utf-8'))
	time.sleep(0.05)
	data = arduino.readline()
	return data

while True:
	num = input("Enter a number: ") # Taking input from user
	print(num) # printing the value
	if num == 'q':
		quit()
	value = write_read(num)
	print(value) # printing the value
