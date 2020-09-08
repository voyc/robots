import socket

# create a UDP client socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print('socket created')

ip = 'localhost'
port = 10000
server_address = (ip,port)
message = b'Please echo this back to me.'
sent = sock.sendto(message, server_address)
print(f'message sent to {server_address}')

data,server = sock.recvfrom(4096)
print(f'received {data} from server {server}')

sock.close()
print('socket closed')
