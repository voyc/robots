'''
https://projecthub.arduino.cc/ansh2919/serial-communication-between-python-and-arduino-663756
'''

import serial
import time

#arduino = serial.Serial(port='COM4',   baudrate=115200, timeout=.1)
arduino = serial.Serial(port='/dev/ttyACM1',   baudrate=115200, timeout=.1)

def write_read(x):
    arduino.write(bytes(x,   'utf-8'))
    time.sleep(0.05)
    data = arduino.readline()
    return   data


#while True:
#    num = input("Enter a number: ")
#    value   = write_read(num)
#    print(value)

def parse(b):
	s = b.decode("utf-8")
	lst = s.split()
	flst = [float(i) for i in lst]
	print(flst)


while True:
	value = write_read("1")
	print(value)
	parse(value)
	time.sleep(1)
