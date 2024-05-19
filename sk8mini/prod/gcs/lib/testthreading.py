'''
testthreading.py

global interpreter lock (GIL) - in CPython, a predominate python interpreter, 
	prevents two threads from executing python code simultaneously,
	sometimes makes multi-threading suboptimal

asyncio
	cooperative multitasking - scheduling/context-switching by app programmer
	coroutine - suspendable unit of work  

thread
	preemptive multitasking, scheduled/context-switched by the OS

blocking
	http can incure latency of 2 or 3 seconds or more
		therefore, blocking between request and response is unthinkable
	over 1700 python libraries for http, and every one of them blocks
	requests.get( url) blocks
	http.client.getResponse() blocks
	urllib.request.urlopen() blocks
	urllib3.PoolManager().request() blocks
	etc

asyncio
	asyncio executes within one thread, and therefore it cannot eliminate the blocking 

therefore we have to use a thread
	we can signal, and/or execute a callback

throttle adjustment is relative to roll, not helm
	therefore, perhaps we should go back to separate commands
	if doing async, we need events
		onRoll - adjust throttle depending on roll
		onHeading - adjust helm to keep course bearing and/or turn radius
		onPosition - override dead-reckoning position

current position:
	x, y, source, where source is dead-reckoning or cv

onReceive

transfer image from camera to python
espnow + serial vs http

serial port baud (bps)
 230400   230.4k
 250000   250.0k
 500000   500.0k  0.5M
1000000  1000.0k  1M
2000000  2000.0k  2M
https://docs.google.com/spreadsheets/d/1Q4BNd_W7z0au821rS-OkA7xuXR-tvCHPNgH-RJ5blN4/edit?usp=sharing


three coroutines:
	awacs
	skate
	ground


'''

# built-in libraries
import threading
import queue
import asyncio
import urllib  # urllib.request.urlopen(url) blocks to wait for response
import requests # blocks
import serial

# not built-in
#import greenlet
#import event - no such thing
#import gevent



event-driven vs async/await

# event-driven model, use event handlers
def onHappening():
	handleIt()

# async/await
def someFunction():
	await happening == True # yield cpu

# threading


for event-driven io, we code two functions:
	1. an inline function readData(filename, buffer, callback) to initiate the read
	2. an event-handler callback to be called when the data has been successfully read into the buffer

for asyncio, we use await 
	def readData(filename, buffer, event):
		...
		event.set()

	def main():
	await event.isSet()


for threading, 


url = 'example.com?get'
Thread.
isresponseready = False

ahttp
requests.get(url)



