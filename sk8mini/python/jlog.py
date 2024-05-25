'''
logger.py - logging wrapper
'''

import logging
import time

def debug(msg):    _log(msg, logging.DEBUG)
def info(msg):     _log(msg, logging.INFO)
def warning(msg):  _log(msg, logging.WARNING)
def error(msg):    _log(msg, logging.ERROR)
def critical(msg): _log(msg, logging.CRITICAL)

def _log(msg, level):
	st = f'{time.time() - timestart:.5f} {msg}'
	logger.log(level, st)	

def setup(verbose, quiet):
	global timestart, logger

	if quiet:	level = logging.CRITICAL
	elif verbose:	level = logging.DEBUG
	else:		level = logging.INFO

	timestart = time.time()
	logging.basicConfig(format='%(message)s') # msg only, on prepends
	logger = logging.getLogger('gcs')  # using our own logger, so we don't see debug messages from imported libraries
	logger.setLevel(level)

# ---- test ---------------------

def main():
	setup(True, False)
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")
	info("")

	setup(False, False)
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")
	info("")

	setup(False, True)
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")
	critical("")

	setup(True, True)    # quiet overrides verbose
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")

if __name__ == '__main__':
	main()

