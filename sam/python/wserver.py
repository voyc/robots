#!/usr/bin/env python

# WS server that sends messages at random intervals
# this template demonstrates asyncio and websockets

import asyncio
import websockets
import datetime
import random

# define the coroutine (thread target fn)
async def time(websocket, path):
	while True:
		now = datetime.datetime.utcnow().isoformat() + "Z"
		await websocket.send(now)
		await asyncio.sleep(random.random() * 3)

async def echo(websocket, path):
	print('echo')
	async for msg in websocket:
		print(msg)
		reply = f'echo: {msg}'
		await websocket.send(msg)
		await asyncio.sleep(.6)
		await websocket.send(reply)

# create server object,  wrapping the cooroutine
server = websockets.serve(echo, "127.0.0.1", 5678)

# start the thread, wrapping the server object
print('get scheduler')
event_loop = asyncio.get_event_loop()  # get the scheduler
print('run until complete')
event_loop.run_until_complete(server)
print('run forever')
event_loop.run_forever()
print('the end')

