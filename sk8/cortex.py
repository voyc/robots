import threading
import time
import monad

class Cortex:
	def __init__(self):
		thread = threading.Thread(target=self.loop)
		thread.start()
		print('cortex started')


	def loop(self):
		maxawake = 10
		counter = 1
		interval = 3
		while monad.state != 'stopped':
			if counter > maxawake:
				break
			counter += 1
			# plan next move, based on mapdata
			# move eyes
			# move wheels	
			time.sleep(interval)
			print('cortex activity')

