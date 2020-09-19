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
		while monad.state != 'stopped':
			ctrAlive += 1
			if ctrAlive > maxAlive:
				print('maxAlive exceeded, shutdown')
				quit()
			if ctrAwake > maxAwake:
				monad.state = 'landing'
			if monad.eyes.checkBattery() == False:
				monad.state = 'landing'
			if monad.eyes.checkTemperature() == False:
				monad.state = 'landing'
			if monad.state == 'landing':
				ctrLanding += 1;
				if ctrLanding == 1:
					rc = monad.eyes.sendCommand('land', wait=True)
					if rc != 'ok':
						print('tello land command failed')
			if monad.state == 'awake':
				ctrAwake += 1
				if ctrAwake == 1:
					rc = monad.eyes.sendCommand('takeoff', wait=True)
					if rc != 'ok':
						print('tello takeoff command failed')	
			if monad.state == 'wakeup':
				rc = monad.eyes.connect()
			if monad.state == 'kill':
				if flying:
					rc = monad.eyes.sendCommand('emergency', wait=True)
				monad.state == 'stopped'	

			# plan next move, based on mapdata
			# move eyes
			# move wheels	
			time.sleep(interval)
			print('cortex activity')

