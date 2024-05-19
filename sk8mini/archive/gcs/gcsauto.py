'''
gcsauto.py - autonomous ground control station

take ideas from 
	hippocam.py - animation skate simulator, nav, pilot
	helix.py - dual 3D graph windows
	../awacs/detect/arduino/arduinopythoncomm.py - get data
'''

from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import matplotlib.pyplot as plt  
from matplotlib.animation import FuncAnimation 
import serial
import time
import random

#accx = np.array([1,2,3,2,1  ])
#accy = np.array([-1,0,1,0,-1])
#accz = np.array([2,3,2,1,0  ])
#t = np.array([1,2,3,4,5  ])

accx = np.array([])
accy = np.array([])
accz = np.array([])
gyrx = np.array([])
gyry = np.array([])
gyrz = np.array([])
magx = np.array([])
magy = np.array([])
magz = np.array([])
tttt = np.array([])

	
fig = plt.gcf()
acc = fig.add_subplot(221)
gyr = fig.add_subplot(222)
mag = fig.add_subplot(223)
att = fig.add_subplot(224, projection='3d')

plotsize = 100


#arduino = serial.Serial(port='COM4',   baudrate=115200, timeout=.1)
#arduino = serial.Serial(port='/dev/ttyACM1',   baudrate=115200, timeout=.1)

def write_read(x):
    arduino.write(bytes(x,   'utf-8'))
    time.sleep(0.05)
    data = arduino.readline()
    return   data

def parse(b):
	s = b.decode("utf-8")
	lst = s.split()
	flst = [float(i) for i in lst]
	print(flst)

def getdata():
	# nine numbers returned from 20948
	readings = np.array([1,2,3,4,5,6,7,8,9])
	for i in range(3,4):
		n = random.randrange(-20000, 20000, 1)
		readings[i] = n
	return readings


def drawplots(t):
	#acc.set_xlim(t-plotsize,t)
	#gyr.set_xlim(t-plotsize,t)
	#mag.set_xlim(t-plotsize,t)
	##att.set_xlim(t-plotsize,t)

	#acc.cla()
	gyr.cla()
	#mag.cla()
	#att.cla()

	#acc.plot(tttt, accx, 'r', lw=1)
	#acc.plot(tttt, accy, 'b', lw=1)
	#acc.plot(tttt, accz, 'g', lw=1)
	gyr.plot(tttt, gyrx, 'r', lw=1, scalex=True, scaley=True)
	#mag.plot(tttt, magz, 'r', lw=1)
	#att.scatter(accx, accy, accz, 'b', lw=2)

def loadarrays(readings, t):
	global accx, accy, accz, gyrx, gyry, gyrz, magx, magy, magz, tttt
	#accx = np.append(accx, readings[0])
	#accy = np.append(accy, readings[1])
	#accz = np.append(accz, readings[2])
	gyrx = np.append(gyrx, readings[3])
	#gyry = np.append(gyry, readings[4])
	#gyrz = np.append(gyrz, readings[5])
	#magx = np.append(magx, readings[6])
	#magy = np.append(magy, readings[7])
	#magz = np.append(magz, readings[8])
	tttt = np.append(tttt, t)
	#if len(accx) > plotsize: accx = accx[1:]
	#if len(accy) > plotsize: accy = accy[1:]
	#if len(accz) > plotsize: accz = accz[1:]
	if len(gyrx) > plotsize: gyrx = gyrx[1:]
	#if len(gyry) > plotsize: gyry = gyry[1:]
	#if len(gyrz) > plotsize: gyrz = gyrz[1:]
	#if len(magx) > plotsize: magx = magx[1:]
	#if len(magy) > plotsize: magy = magy[1:]
	#if len(magz) > plotsize: magz = magz[1:]
	if len(tttt) > plotsize: tttt = tttt[1:]

def printall():
	print(accx)
	print(accy)
	print(accz)
	print(gyrx)
	print(gyry)
	print(gyrz)
	print(magx)
	print(magy)
	print(magz)

def animate(t):
	readings = getdata()
	loadarrays(readings, t)
	drawplots(t)
	

def main():
	anim = FuncAnimation(fig, animate)
	plt.show()

if __name__ == '__main__':
	main()

