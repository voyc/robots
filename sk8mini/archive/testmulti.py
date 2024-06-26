import multiprocessing as mp
import time


def childloop():
	for i in range(5):
		print('wa wa')
		time.sleep(.5)

def main():
	mychild = mp.Process(target=childloop)
	mychild.start()
	print('child started')
	#mychild.join()  # blocks the parent here until child ends
	print('child joined')

if __name__ == '__main__':
	main()
	print('by default, waits here for child to finish')
