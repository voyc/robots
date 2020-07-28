import socket

# create a socket.  INET==IPv4, STREAM==TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('socket created')

# connect to a remote server
ip = socket.gethostname()
ip = 'localhost'
port = 80
port = 4567
s.connect((ip,port))
print('connect to '+ip+':'+str(port))

maxlen = 1024
msg = s.recv(maxlen)
print(msg.decode('utf-8'))

