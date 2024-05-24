'''
smem.py

shared memory used by 3 threads: gcs, awacs, skate

Route:
	leg - a tuple of (legnum, conenum, side)
	pattern - a list of up to 10 legs
	route - the complete list of legs
	
	The navigator adds patterns to the route periodically.
	The pilot accomplishes each leg in the route sequentially and continuously.

usage:
# shared memory, instantiate in gcs.py
smem_timestamp = multiprocessing.Array('d', range(0, TIME_ARRAY_SIZE))
smem_positions = multiprocessing.Array('i', range(0, POS_ARRAY_SIZE))

# pass args to each new process
awacs_process = multiprocessing.Process(target=awacs_main, args=(smem_timestamp, smem_positions))
'''

# global constants
MAX_CONES	= 10
MAX_LEGS	= 10

# map smem_timestamp
TIME_KILLED		= 0
TIME_DONUT_CHANGED	= 1
TIME_CONES_CHANGED	= 2
TIME_HEADING_CHANGED	= 3
TIME_ROUTE_CHANGED	= 4
TIME_ARRAY_SIZE		= 5

# map smem_positions
NUM_CONES	= 0
NUM_LEGS	= 1
DONUT_X		= 2
DONUT_Y		= 3
SKATE_X		= 4
SKATE_Y		= 5
SKATE_HDG	= 6
SKATE_ROLL	= 7
CONE1_X		= 8
CONE1_Y		= 9
CONEMAX_Y	= CONE1_X + MAX_CONES * 2
LEG1_LEGNUM	= CONEMAX_Y + 1
LEG1_CONENUM	= CONEMAX_Y + 2
LEG1_SIDE	= CONEMAX_Y + 3
LEGMAX_SIDE	= CONEMAX_Y + MAX_LEGS * 3
POS_ARRAY_SIZE	= LEGMAX_SIDE + 1

