import socket

# create a socket.  INET==IPv4, STREAM==TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('socket created')

#bind the socket to a ip/port
ip = socket.gethostname()
ip = 'localhost'
ip = ''
port = 80
port = 4567
s.bind((ip, port))
print('bind to '+ip+':'+str(port))

# become a server socket, queue a maximum 5 connections
s.listen(5)
print('listening')

while True:
    # accept connections from outside
    (clientsocket, (cip,cport)) = s.accept()
    print('accepted connection from ' + cip + ':' + str(cport))

    clientsocket.send(bytes('welcome from port '+str(cport),'utf-8'))
 
    # now do something with the clientsocket
    # in this case, we'll pretend this is a threaded server
#    ct = client_thread(clientsocket)
#    ct.run()
