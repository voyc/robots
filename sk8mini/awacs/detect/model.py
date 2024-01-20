'''
model.py - model management library

A model is a python dict with parameters used for object detecion within an image.
It is stored in a json file, usually named model.json.
'''

import json
def read(fname):
	with open(fname, 'r') as f:
		model = json.load(f)
	return model

def write(model, fname, expand=False):
	extractValues(model)
	with open(fname, 'w') as f:
		if expand:
			f.write(json.dumps(model, indent=4))
		else:
			f.write(json.dumps(model))

def format(model, style):
	s = ''
	if style == 'dump': 
		s = json.dumps(model)
	elif style == 'indent':
		s = json.dumps(model, indent=4)
	elif style == 'pretty':
		for n in model:
			modcls = model[n]
			for param in modcls:
				if param == 'spec':
					for sp in modcls['spec']:
						s += f"{sp}\n"
				else:

					s += f"{param}: {str(modcls[param])} \n"
			s += '\n'
	elif style == 'simple':
		extractValues(model)
		for modcls in model:
			for param in modcls:
				if param != 'spec':
					s += f"{param}: {str(modcls[param])} \n"
			s += '\n'
	return s

def extractValues(model):
	for modcls in model:
		values = []
		for sp in modcls['spec']:
			values.append(sp['value'])
		modcls['values'] = values
	return values

# loop thru cls and spec
def initialize(model, cls='all'):
	for classifier in model:
		if cls != 'all' and cls != classifier:
			continue
		modcls = model[classifier]
		spec = modcls['spec']
		for sp in spec:
			if sp['way'] > 0:
				sp['value'] = sp['lower']
			else:
				sp['value'] = sp['upper']

