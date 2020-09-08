import socket

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the port
ip = 'localhost'
port = 10000
server_address = (ip,port)
sock.bind(server_address)
print(f'bind to {ip}:{port}')

while True:
    data,address = sock.recvfrom(4096)
    print(f'received {len(data)} bytes from client {address}')

    if data:
        sent = sock.sendto(data, address)
        print(f'echoed back')
