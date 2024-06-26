'''
testoop.py
'''
import time

class Sk8:
	helm = 0
	throttle = 0
	paused = False
	t = 0.0

	def isPaused(self):
		return self.paused

	def pause(self):
		self.paused = True

	def unpause(self):
		self.paused = False

class Photo:
	donut = 1
	t = 0.0
	def set(self, val): self.donut = val; self.t = time.time() 

def main():
	sk8 = Sk8()
	print(sk8.isPaused())
	sk8.pause()
	print(sk8.isPaused())
	sk8.unpause()
	print(sk8.isPaused())
	print(sk8.paused)

	photo = Photo()
	print(photo.donut)
	print(photo.t)
	photo.set(3)
	print(photo.donut)
	print(photo.t)
	

if __name__ == '__main__':
	main()
