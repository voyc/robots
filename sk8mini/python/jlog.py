'''
jlog.py - logging wrapper
'''

import logging
import time

def debug(msg):    _log(msg, logging.DEBUG)	# 10
def info(msg):     _log(msg, logging.INFO)	# 20
def warning(msg):  _log(msg, logging.WARNING)	# 30
def error(msg):    _log(msg, logging.ERROR)	# 40
def critical(msg): _log(msg, logging.CRITICAL)	# 50

timestart = 0.0
unit = 'setup'

def _log(msg, level):
	st = f'{time.time() - timestart:.5f} {unit} {level}: {msg}'
	logger.log(level, st)	

def setup(component, verbose, quiet):
	global timestart, logger, unit

	if quiet:	level = logging.ERROR #CRITICAL
	elif verbose:	level = logging.DEBUG
	else:		level = logging.INFO

	timestart = time.time()
	unit = component
	logging.basicConfig(format='%(message)s') # msg only, on prepends
	logger = logging.getLogger('gcs')  # using our own logger, so we don't see debug messages from imported libraries
	logger.setLevel(level)

# ---- test ---------------------

def main():
	setup('setup', True, False)
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")
	info("")

	setup('setup', False, False)
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")
	info("")

	setup('setup', False, True)
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")
	critical("")

	setup('setup', True, True)    # quiet overrides verbose
	debug("This is a sample debug message")
	info("This is a sample info message")
	warning("This is a sample warning message")
	error("This is a sample error message")
	critical("This is a sample critical message")

if __name__ == '__main__':
	main()

