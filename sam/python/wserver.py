#!/usr/bin/env python

# WS server that sends messages at random intervals
# this template demonstrates asyncio and websockets

import asyncio
import websockets
import datetime

ip = '127.0.0.1'
port = 5678
hostname = 'Host'
timeout = datetime.timedelta(seconds=120)

clients = {}
recent = datetime.datetime.now()

async def hostinterject(message):
	recent = datetime.datetime.now()
	print(f'{recent} {message}')
	msg = f'{hostname}~{message}'	
	await broadcast(msg)

async def broadcast(msg):
	for usr in clients:
		try:
			await clients[usr].send(msg)
		except:
			pass

async def serveloop(websocket, path):
	global recent
	print(websocket)
	async for message in websocket:
		recent = datetime.datetime.now()
		print(f'{recent} {message}')
		cmd,usr,msg = message.split('~')
		if cmd == 'login':
			clients[usr] = websocket
			reply = f'{hostname}~Welcome, {usr}'	
		elif cmd == 'logout':
			del clients[usr]
			reply = f'{hostname}~Goodbye, {usr}'
		elif cmd == 'message':
			reply = f'{usr}~{msg}'
		await asyncio.sleep(.6)
		await broadcast(reply)

async def wakeup():
	global recent
	while True:
		await asyncio.sleep(30)
		now = datetime.datetime.now()
		diff = now - recent
		if diff > timeout:
			await hostinterject('Are you still here?')
			recent = now

server = websockets.serve(serveloop, ip, port) # create server, wrapping coroutine
event_loop = asyncio.get_event_loop()  # get the scheduler
event_loop.run_until_complete(server)  # make connection, wrapping server object
asyncio.ensure_future(wakeup())
print('serving websockets...')
event_loop.run_forever()

