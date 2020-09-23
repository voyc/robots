import threading
import time
import monad

class Cortex:
	def __init__(self):
		thread = threading.Thread(target=self.loop)
		thread.start()
		print('cortex started')


	def loop(self):
		ctrAlive = 0
		maxAlive = 40
		ctrAwake = 0
		maxAwake = 20
		interval = 1
		ctrLanding = 0

asleep
awake
	waking
		connecting
		initing
		rtf
	flying
		takeoff
		plotting map (exploring for cones
			plan move
			execute
		showing off (running courses)
			plan move
			execute
	homing (return to home)
		plan move
		execute
	home
	stopped (not necessarily at home, could conceivably resume)
shutdown

command
	start
	stop
	resume
	land
	kill

		while monad.state != 'shutdown':
			if monad.state == 'sleeping':
				pass

			if monad.state == 'wakeup':
				pass

			if monad.state = 'awake':
				# check viability of continued operation
				ctrAlive += 1
				if ctrAlive > maxAlive:
					monad.log('maxAlive exceeded, shutdown')
					self.command('kill')
				if ctrAwake > maxAwake:
					monad.log('maxAwake exceeded, homing')
					self.command('stop')
				if monad.eyes.checkBattery() == False:
					monad.log('low battery, homing')
					self.command('home')
				if monad.eyes.checkTemperature() == False:
					monad.log('high temperature, homing')
					self.command('home')

			if monad.state == 'homing':
				ctrLanding += 1;
				if ctrLanding == 1:
					rc = monad.eyes.sendCommand('home', wait=True)
					if rc != 'ok':
						print('tello home command failed')

			if monad.state == 'wakeup':
				nw = monad.eyes.isConnectedTo()
				if nw[0:5] == 'TELLO':
					rc = monad.eyes.init()
					if rc:
						monad.state = 'awake'
					else:
						print('awake, rtf')
						monad.state = 'shutdown'
				else:
					print('TELLO wifi not connected. Please connect now.')

			if monad.state == 'rtf':
				ctrAwake += 1
				if ctrAwake == 1:
					rc = monad.eyes.sendCommand('takeoff', wait=True)
					if rc:
						monad.state = 'flying'
						print('flying')
					if rc != 'ok':
						print('tello takeoff command failed')	
			if monad.state == 'kill':
				if flying:
					rc = monad.eyes.sendCommand('emergency', wait=True)
				monad.state == 'stopped'	

			if monad.state == 'flying':
				# plan next move, based on mapdata
				# move eyes
				# move wheels	
				monad.log('flying')
			else:
				monad.log('thinking')
			time.sleep(interval)

	def command(self, cmd):
		if cmd == 'go':
			monad.eyes.go()
			#monad.wheels.go()
		elif cmd == 'stop':
			monad.eyes.stop()
			#monad.wheels.stop()
		elif cmd == 'home':
			monad.eyes.home()
			#monad.wheels.home()
		elif cmd == 'kill':
			monad.eyes.kill()
			#monad.wheels.kill()
