'''
smem.py

shared memory used by 3 threads: gcs, awacs, skate

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

# map smem_timestamp, all double floats
TIME_KILLED	= 0
TIME_PHOTO	= 1
TIME_ARRAY_SIZE	= 2

# map smem_positions, all integers
NUM_CONES	= 0
NUM_LEGS	= 1
DONUT_X		= 2
DONUT_Y		= 3
CONE1_X		= 4
CONE1_Y		= 5
CONEMAX_Y	= CONE1_X + MAX_CONES * 2
POS_ARRAY_SIZE	= CONEMAX_Y + 1

