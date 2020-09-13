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

# UDP client socket to send and receive commands
cmdsock = False
cmdsock_timeout = 10 
tello_ip = '192.168.10.1'
cmd_port = 8889  # may need to open firewall to these ports
tele_port = 8890
video_port = 11111
tello_address = (tello_ip, cmd_port)
cmdmaxlen = 1518

# UDP server socket to receive telemetry data
telemetrysock = False
telemetrysock_timeout = 10 
telemetry_address = ('',8890)
telemetry_maxlen = 1518 #?
telemetry_thread = False
telemetry_thread_status = 'init' # init, stopping, running
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

# function to send command and get return message
# The demo programs create a thread with a loop doing the recvfrom.  Why? Can the recvfrom block?
def sendCommand(cmd):
    global cmdsock,tello_address
    rmsg = 'error'
    try:
        msg = cmd.encode(encoding="utf-8")
        len = cmdsock.sendto(msg, tello_address)
    except Exception as ex:
        log (cmd + ' sendto failed:'+str(ex))
    else:
        log(cmd)
        try:
            data, server = cmdsock.recvfrom(cmdmaxlen)
            rmsg = data.decode(encoding="utf-8")
        except Exception as ex:
            log (cmd + ' recvfrom failed:'+str(ex))
        else:
            log(cmd + ' : ' + rmsg)
    return rmsg;

# function to receive string of telemetry data
def telemetryLoop():
    global telemetry, telemetry_thread_status, telemetry_thread
    count = 0
    while True: 
        if telemetry_thread_status == 'stopping':
            break;
        try:
            data, server = telemetrysock.recvfrom(telemetry_maxlen)
        except Exception as ex:
            log ('Telemetry recvfrom failed: ' + str(ex))
            break
        count += 1
        storeTelemetry(data)
        if count%10 == 0:
            log(data.decode(encoding="utf-8"))

        # check battery and temperature
        log('battery:' + str(telemetry['bat']) + ', high temperature:' + str(telemetry['temph']))

def startTelemetry():
    global telemetry_thread_status, telemetry_thread
    telemetry_thread = threading.Thread(target=telemetryLoop)
    telemetry_thread.start()
    telemetry_thread_status = 'running'

def stopTelemetry():
    global telemetry_thread_status, telemetry_thread
    if telemetry_thread_status == 'running':
        telemetry_thread_status = 'stopping'
        telemetry_thread.join()
        
def storeTelemetry(data):
    # data=b'pitch:-2;roll:-2;yaw:2;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:6553;h:0;bat:42;baro:404.45;time:0;agx:-37.00;agy:48.00;agz:-1008.00;'
    global telemetry
    sdata = data.decode('utf-8')
    adata = sdata.split(';')
    for stat in adata:
        if len(stat) <= 2: # last item is cr+lf
            break
        name,value = stat.split(':')
        if name in ['baro','agx','agy','agz']:
            telemetry[name] = float(value);
        else:
            telemetry[name] = int(value);
    
# function to receive string of video data
def videoLoop():
    global video, video_thread_status, video_thread
    count = 0
    while True: 
        if video_thread_status == 'stopping':
            break;
        try:
            data, server = videosock.recvfrom(video_maxlen)
        except Exception as ex:
            log ('Video recvfrom failed: ' + str(ex))
            break
        count += 1
        #if count%10 == 0:
        #    storeVideo(data)

        cap = cv.VideoCapture('udp://'+tello_ip+':'+video_port)
        if not cap.isOpened():
            print("Cannot open camera")
            stop()
        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()
            # if frame is read correctly ret is True
            if not ret:
                print("Can't receive frame (stream end?). Exiting ...")
                break
            # Our operations on the frame come here
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            # Display the resulting frame
            cv.imshow('frame', gray)
            if cv.waitKey(1) == ord('q'):
                break
            # When everything done, release the capture
            cap.release()
            cv.destroyAllWindows()

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

# start
mode = 'prod'
for i, arg in enumerate(sys.argv):
    if arg == 'test':
        mode = 'test'
log ('eyes starting ' + mode)

# test
if mode == 'test':
    cap = cv.VideoCapture('udp://'+str(tello_ip)+':'+str(video_port))
    quit()

# Create cmd socket as UDP client
cmdsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cmdsock.settimeout(cmdsock_timeout)
#sock.bind(locaddr) # bind is for server ???

# Create telemetry socket as UDP server
telemetrysock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
telemetrysock.settimeout(telemetrysock_timeout)
telemetrysock.bind(telemetry_address) # bind is for server, not client

# Create video socket as UDP server
videosock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
videosock.settimeout(videosock_timeout)
videosock.bind(video_address) # bind is for server, not client

# send the "command" command to start receiving the data stream
cmd = sendCommand("command")
if cmd == 'ok':
    batt = sendCommand("battery?")
    if int(batt) < 20:
        log('battery low.  aborting.')

    else:
        startTelemetry() 
        so = sendCommand("streamon")
        startVideo()
        time.sleep(int(5))
        #flyMission(takeoffland)
        #flyMission(testheight)
        #flyMission(demo)
        stopTelemetry()
        stopVideo()

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

