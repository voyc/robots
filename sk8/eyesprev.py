# eyes.py
# The eyes of the sk8 robot.

import socket
import time
from time import strftime
from datetime import datetime
import threading 
import sys
import numpy as np
import cv2 as cv

class Eyes():
	__init__()
	print('eyes starting')

# missions
takeoffland = ('takeoff\n'
               'sleep 3\n'
               'land')
testheight  = ('height?\n'
               'tof?\n'
               'baro?')
demo        = ('takeoff\n'
               'up 20\n'
               'cw 360\n'
               'right 20\n'
               'land')


# UDP server socket to receive telemetry data
telemetry = {
    "pitch":-2,
    "roll":-2,
    "yaw":2,
    "vgx":0,
    "vgy":0,
    "vgz":0,
    "templ":62,
    "temph":65,
    "tof":6553,
    "h":0,
    "bat":42,
    "baro":404.45,
    "time":0,
    "agx":-37.00,
    "agy":48.00,
    "agz":-1008.00}

# UDP server socket to receive video stream
videosock = False
videosock_timeout = 10 
video_address = ('',11111)

video_maxlen = 1518 #?
video_thread = False
video_thread_status = 'init' # init, stopping, running

# function to print string with timestamp
def log(s):
    tm = datetime.now().strftime("%H:%M:%S.%f")
    print(tm + ' ' + s)

# function to run a mission
def flyMission(s):
    a = s.split('\n')
    for cmd in a:
        if cmd[0:5] == 'sleep':
            log(cmd)
            n = cmd.split(' ')[1]
            time.sleep(int(n))
        else:
            sendCommand(cmd)

def startVideo():
    global video_thread_status, video_thread
    video_thread = threading.Thread(target=videoLoop)
    video_thread.start()
    video_thread_status = 'running'

def stopVideo():
    global video_thread_status, video_thread
    if video_thread_status == 'running':
        video_thread_status = 'stopping'
        video_thread.join()
        
def stop():
    cmdsock.close()
    telemetrysock.close()
    videosock.close()
    log ('eyes shutdown')
    quit()

# video thread

# telemetry thread

# recvfrom thread (ignore)

# eyes commands
# go
# end
# fly
# stop


# stop 
stop()
quit()


# # send user commands from keyboard
# while True: 
#     try:
#         msg = input("");
#         if not msg or 'quit' in msg:
#             break
#         msg = msg.encode(encoding="utf-8") 
#         sent = sock.sendto(msg, tello_address)
#         log( sent);
#     except KeyboardInterrupt:
#         break

