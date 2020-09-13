import threading
import time
import state

class Brain:
	def __init__(self):
		thread = threading.Thread(target=self.loop)
		thread.start()
		print('brain started')

	def loop(self):
		while state.state != 'stopped':
			# plan next move, based on mapdata
			# move eyes
			# move wheels	
			time.sleep(1)
			print('brain activity')

