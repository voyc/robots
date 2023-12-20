import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-v'  ,'--verbose'        ,default=False                ,action='store_true'          ,help='display additional output messages.'                        ),
parser.add_argument('-q'  ,'--quiet'          ,default=False                ,action='store_true'          ,help='suppresses all output.'                                     ),
spec = parser.parse_args()	# returns Namespace object, use dot-notation


logging.basicConfig(format='%(message)s')
logging.getLogger('').setLevel(logging.INFO)
if spec.verbose:
	logging.getLogger('').setLevel(logging.DEBUG)
if spec.quiet:
	logging.getLogger('').setLevel(logging.CRITICAL)

print(logging.getLogger('').level)

logging.critical(f'level critical {logging.CRITICAL}')
logging.error(   f'level error {logging.ERROR}')
logging.warning( f'level warn {logging.WARN}')
logging.info(    f'level info {logging.INFO}')
logging.debug(   f'level debug {logging.DEBUG}')
