#
# Tello Python3 Control Demo 
#
# http://www.ryzerobotics.com/
#
# 1/1/2018

import threading 
import socket
import sys
import time
import platform  

host = ''
port = 9000
locaddr = (host,port) 

# starting
print ('Tello Python3 Demo')
print ('Enter command or "quit"')

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tello_address = ('192.168.10.1', 8889)
sock.bind(locaddr)

# send the "command" command to start receiving the data stream
try:
    msg = 'command';
    msg = msg.encode(encoding="utf-8")
    sent = sock.sendto(msg, tello_address)
except Exception:
    print ('command command failed\n')
    sock.close()
    quit()

# receive-telemetry thread
thread_status = 'init'

def recv():
    count = 0
    while True: 
        if thread_status == 'stopping':
            break;
        try:
            data, server = sock.recvfrom(1518)
            print(data.decode(encoding="utf-8"))
        except Exception as ex:
            print ('Exception in receive-telemetry: ' + ex + '\n')
            break

def stoprecv():
    global thread_status
    if thread_status == 'running':
        thread_status = 'stopping'
        recvThread.join()
        
recvThread = threading.Thread(target=recv)
recvThread.start()
thread_status = 'running'

# send user commands from keyboard
while True: 
    try:
        msg = input("");
        if not msg or 'quit' in msg:
            break
        msg = msg.encode(encoding="utf-8") 
        sent = sock.sendto(msg, tello_address)
        print( sent);
    except KeyboardInterrupt:
        break

stoprecv()
sock.close()
print ('finished')

