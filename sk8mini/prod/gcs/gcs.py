'''
gcs.py  ground control station

runs on laptop
connect to the dongle via serial port
the dongle is an Arduino Nano ESP32 running gcs.ino

receive heading and roll from sk8 via serial port dongle
connect to awacs webserver and download photos
detct donut and cone positions from the awacs
navigate
pilot
send pilot commands through the dongle to sk8

gcs.py object detection
folder:  ~/webapps/robots/robots/sk8mini/awacs/detect/
    testconvolve.py  - find donut
        idir = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
        odir = '/home/john/media/webapps/sk8mini/awacs/photos/training/labels/'
    scanorm.py - scan a folder of images and a folder of labels, draw the label circle onto the image
    still need the latest find cone algorithm...



~/webapps/robots/robots/sk8mini/pilot
	pilot.ino - helm and throttle implemented via espwebserver
	pilot.py - manual piloting via keyboard as webserver client


'''

import serial
import time

#arduino = serial.Serial(port='COM4',   baudrate=115200, timeout=.1)
#arduino = serial.Serial(port='/dev/ttyACM0',   baudrate=115200, timeout=.1)
arduino = serial.Serial(port='/dev/ttyUSB0',   baudrate=115200, timeout=.1)

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


