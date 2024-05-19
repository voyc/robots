'''
printmodel.py - format and print a model
'''
import os
import argparse
import model as mod

global gargs

def main():
	global gargs

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-im' ,'--model'     ,default='model.json'   ,help='input model filename.'   )
	parser.add_argument('-f'  ,'--format'    ,default='simple'       ,choices=['dump','indent','pretty','simple']  ,help='output format.'   )
	parser.add_argument('-rx' ,'--rewrite_expand'    ,default=False  ,action='store_true' ,help='output format.'   )
	parser.add_argument('-rc' ,'--rewrite_collapse'  ,default=False  ,action='store_true' ,help='output format.'   )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	model = mod.read(gargs.model)
	print(f'read {gargs.model}')

	s = mod.format(model, gargs.format)
	print(f'{s}\n')

	if gargs.rewrite_expand:
		ch = input(f'model file will be rewritten. Continue? (y/n)')
		if ch == 'y':
			mod.write(model, gargs.model, expand=True)
			print('expanding')

	if gargs.rewrite_collapse:
		ch = input(f'model file will be rewritten. Continue? (y/n)')
		if ch == 'y':
			mod.write(model, gargs.model, expand=False)
			print('collapsing')

if __name__ == '__main__':
	main()
