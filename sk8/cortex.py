# cortex.py

import threading
import time
import monad


# state machine
#	asleep
#	waking
#	connected
#	ready
#		flying
#			taking off
#			plotting map (exploring for cones

# state machine
#	asleep
#	awake
#		waking
#			connected
#			initing
#			rtf
#		flying
#			taking off
#			plotting map (exploring for cones
#				plan move
#				execute
#			showing off (running courses)
#				plan move
#				execute
#			homing (return to home)
#				plan move
#				execute
#			landing
#		grounded
#			home
#			stranded
#	shutdown

class Cortex:
	maxAlive = 40
	maxAwake = 20
	interval = 1
	connectionTimeout = 5
	startTimeout = 20

	def __init__(self):
		self.state = 'asleep' # asleep, awake, shutdown
		self.wakestate = '' # waking, connected, ready, flying
		self.ctrAlive = 0
		self.ctrAwake = 0
		self.ctrLanding = 0
		self.ctrConnectWarning = 0

		thread = threading.Thread(target=self.loop)
		thread.start()
		print('cortex started')


	def loop(self):
		while True:
			time.sleep(self.interval)
			self.ctrAlive += 1
			if self.state == 'shutdown':
				break  # end loop, stop thread
			if self.state == 'awake':
				self.ctrAwake += 1
			viable = self.checkVitals()
			if not viable: 
				self.command('kill')
				break

			if self.wakestate == 'waking':
				connected = monad.eyes.checkConnection()
				if connected:
					self.state = 'connected' 
				else:
					if self.ctrAlive < self.connectionTimeout:
						if self.ctrConnectWarning > 0:
							monad.log('not connected.  Please connect now...')
							self.ctrConnectWarning += 1
					else:
						monad.log('not connected timeout.')
						self.command('kill')

			if self.wakestate == 'connected':	
				eyesopen = monad.eyes.open()
				if eyesopen:
					self.state = 'ready'
				else:
					monad.log('eyes open failed')
					self.command('kill')
				#monad.wheels.wake()


			#if monad.state == 'wakeup':
			#	nw = monad.eyes.getConnection()
			#	if nw[0:5] == 'TELLO':
			#		rc = monad.eyes.init()
			#		if rc:
			#			monad.state = 'awake'
			#		else:
			#			print('awake, rtf')
			#			monad.state = 'shutdown'
			#	else:
			#		print('TELLO wifi not connected. Please connect now.')

			#if monad.state == 'rtf':
			#	self.ctrAwake += 1
			#	if self.ctrAwake == 1:
			#		rc = monad.eyes.sendCommand('takeoff', wait=True)
			#		if rc:
			#			monad.state = 'flying'
			#			print('flying')
			#		if rc != 'ok':
			#			print('tello takeoff command failed')	
			#if monad.state == 'kill':
			#	if flying:
			#		rc = monad.eyes.sendCommand('emergency', wait=True)
			#	monad.state == 'stopped'	

			#if monad.state == 'flying':
			#	# plan next move, based on mapdata
			#	# move eyes
			#	# move wheels	monad.log('flying') else:
			#	monad.log('thinking')

	def plot(self):
		pass

	def execute(self):
		pass


	def checkVitals(self):
		rc = True
		if self.ctrAlive > self.maxAlive:
			monad.log('maxAlive exceeded')
			rc = False
		if self.state == 'ready' and self.ctrAlive > self.startTimeout: 
			monad.log('bored')
			rc = False
		if self.ctrAwake > self.maxAwake:
			monad.log('maxAwake exceeded')
			rc = False
		if monad.eyes.checkBattery() == False:
			monad.log('low battery')
			rc = False
		if monad.eyes.checkTemperature() == False:
			monad.log('high temperature')
			rc = False
		return rc

	def command(self, cmd):
		if cmd == 'start':
			self.wakestate = 'starting'
			monad.eyes.start()
			#monad.wheels.start()
		elif cmd == 'stop':
			monad.eyes.stop()
			#monad.wheels.stop()
		elif cmd == 'resume':
			monad.eyes.resume()
			#monad.wheels.resume()
		elif cmd == 'home':
			#if self.wakestate == 'flying'
			monad.eyes.home()
			#monad.wheels.home()
		elif cmd == 'kill':
			self.state = 'shutdown'
			monad.eyes.kill()
			#monad.wheels.kill()
		elif cmd == 'wakeup':
			self.state = 'awake'
			self.wakestate = 'waking'
			#monad.wheels.wake()

