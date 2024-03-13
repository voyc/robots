'''
traincones.py
'''

import argparse
import logger
import awacsim as awacs
import vistek

deffolder = '/home/john/media/webapps/sk8mini/awacs/photos/training/'

def training():
	dim = (22,22)
	weight = .8
	bias = 115
	minp = .5
	model = [dim, weight, bias, minp]
	labels = forward(model)
	if not len(labels): return []
	#print(labels)
	# read all images
	# read ground truth
	# compare labels to truth
	# adjust model
	return labels

def forward(model):
	frame, fnum = awacs.getFrame()
	if not len(frame): return []
	labels = vistek.getCones(frame, model)
	logger.info(f'frame {fnum}: {len(labels)} labels') 

	#truth = readGroundTruth(fnum)
	#error = coneLossFunction(truth, labels)


	#try again

	return labels

def lossf(predicted, actual):
	pass

def getArgs():
	parser = argparse.ArgumentParser()
	parser.add_argument('-v'  ,'--verbose'   ,action='store_true' ,default=False   ,help='display additional logging'    ),
	parser.add_argument('-q'  ,'--quiet'     ,action='store_true' ,default=False   ,help='suppresses all output'                 ),
	parser.add_argument('-f'  ,'--folder'                         ,default=deffolder,help='folder'                 ),
	args = parser.parse_args()	# returns Namespace object, use dot-notation
	return args

def main():
	global ssid, sspw
	args = getArgs()
	logger.setup(args.verbose, args.quiet)
	logger.info('starting')
	logger.debug(args)

	rc = awacs.setup(args.folder)
	if not rc: return
	logger.info('awacs online')

	rc = vistek.setup()
	if not rc: return
	logger.info('vistek online')

	logger.info('go - press ctrl-c to stop')
	try:
		# training
		while True:
			frm = training()
			if not len(frm):
				logger.info(f'stopped due to no input from awacs')
				break
	except KeyboardInterrupt:
		logger.br(); logger.info(f'operator panic stop')

if __name__ == '__main__':
	main()

