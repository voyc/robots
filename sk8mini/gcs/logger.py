'''
logger.py - logging wrapper
'''

import logging
import time

timestart = 0
elapsedformat = '%.5f'

def debug(msg):    _log(msg, logging.DEBUG)
def info(msg):     _log(msg, logging.INFO)
def warning(msg):  _log(msg, logging.WARNING)
def error(msg):    _log(msg, logging.ERROR)
def critical(msg): _log(msg, logging.CRITICAL)

def _log(msg, level):
	st = f'{time.time() - timestart:.5f} {msg}'
	logging.log(level, st)	

def br():
	logging.log(logging.INFO, '')

def setup(verbose, quiet):
	global timestart
	logging.basicConfig(format='%(message)s')
	if verbose: level = logging.DEBUG
	elif quiet: level = logging.CRITICAL
	else: level = logging.INFO
	logging.getLogger('').setLevel(level)
	timestart = time.time()

def main():
	setup(True,False)
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")

if __name__ == '__main__':
	main()

