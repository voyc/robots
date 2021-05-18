# cortex.py

import threading
import time
import monad

# state machine
#	state		wakestate     
#	asleep		sleeping
#	awake		waking
#	awake		connected
#	awake		ready
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
	connectTimeout = 5
	startTimeout = 20

	def __init__(self):
		self.state = 'asleep' # awake, shutdown
		self.wakestate = 'sleeping' # waking, connected, ready, flying
		self.ctrAlive = 0
		self.ctrAwake = 0
		self.ctrLanding = 0
		self.ctrConnectWarning = 0

		thread = threading.Thread(target=self.loop)
		thread.start()
		monad.log('cortex thread started')


	def loop(self):
		while True:
			time.sleep(self.interval)
			monad.log('thinking')
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
					self.wakestate = 'connected' 
				else:
					if self.ctrAlive < self.connectTimeout:
						if self.ctrConnectWarning <= 0:
							monad.log('not connected.  Please connect now...')
							self.ctrConnectWarning += 1
					else:
						monad.log('not connected timeout.')
						self.command('kill')

			if self.wakestate == 'connected':	
				eyesopen = monad.eyes.open()
				if eyesopen:
					self.wakestate = 'ready'
				else:
					monad.log('eyes open failed')
					self.command('kill')
				#monad.wheels.wake()
		monad.log('exit cortex thread')

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
			monad.log(f'temp: {monad.telem["temph"]}')
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

