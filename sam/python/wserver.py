#!/usr/bin/env python

# WS server that sends messages at random intervals
# this template demonstrates asyncio and websockets

import asyncio
import websockets
import datetime
import random

ip = '127.0.0.1'
port = 5678
clients = {}

# define the coroutine (thread target fn)
async def time(websocket, path):
	while True:
		now = datetime.datetime.utcnow().isoformat() + "Z"
		await websocket.send(now)
		await asyncio.sleep(random.random() * 3)

async def broadcast(msg):
	for usr in clients:
		try:
			await clients[usr].send(msg)
		except:
			pass

async def echo(websocket, path):
	print(websocket)
	async for message in websocket:
		print(message)
		cmd,usr,msg = message.split('~')
		if cmd == 'login':
			clients[usr] = websocket
			reply = f'Host~Welcome, {usr}'	
		elif cmd == 'logout':
			del clients[usr]
			reply = f'Host~Goodbye, {usr}'
		elif cmd == 'message':
			reply = f'{usr}~{msg}'
		await asyncio.sleep(.6)
	#	for usr in clients:
	#		try:
	#			await clients[usr].send(reply)
	#		except:
	#			pass
		await broadcast(reply)

# create server object,  wrapping the cooroutine
server = websockets.serve(echo, ip, port)

# start the thread, wrapping the server object
event_loop = asyncio.get_event_loop()  # get the scheduler
event_loop.run_until_complete(server)
print('serving websockets...')
event_loop.run_forever()
