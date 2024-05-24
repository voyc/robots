import multiprocessing
import signal
import time

kill_time = multiprocessing.Value('d', 0.0)

def main():
	global sub_process, kill_time
	try:
		sub_process = multiprocessing.Process(target=sub, args=(kill_time,))
		sub_process.start()
		for i in range(10):
			print('main working')
			time.sleep(1)
	except KeyboardInterrupt:
		print('catch keyboard interrupt in main')
		kill_time.value = time.time()
	except:
		raise
	print('main exit')


def sub(kill_switch):
	try:
		# ignore the KeyboardInterrupt in this subprocess
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		
		for i in range(20):
			if kill_switch.value:
				break
			print('sub working')
			time.sleep(.5)
	except KeyboardInterrupt:
		pass  # never happen
	except:
		raise
	print('sub exit')
		
main()

