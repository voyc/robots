'''
model.py - model management library

a model is a python dict with parameters used for object detecion within an image
it is stored in a json file, usually named model.json
'''

import json

def read(fname):
	with open(fname, 'r') as f:
		model = json.load(f)
	return model

def write(model, fname):
	with open(fname, 'w') as f:
		f.write(json.dumps(model, indent=4))

def dump(model):
	s = json.dumps(model, indent=4)
	return s

def format(model):
	s = ''
	for n in model:
		s += f"{model[n]['cls']} {model[n]['name']}\n"
		for sp in model[n]['spec']:
			s += f"{sp}\n"
		s += f"{model[n]['size']}\n"
	return s

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

# ------------------- unit test ------------------------- #

def main():
	example_model = {
		"1":{
		"cls":1,
		"name":"cone",
		"algo":0,
		"spec":[
			{"name":"hue_min", "value": 23, "lower":0, "upper":255, "way":1, "incr":[30,10,1]},
			{"name":"hue_max", "value": 37, "lower":0, "upper":255, "way":-1, "incr":[30,10,1]},
			{"name":"sat_min", "value":114, "lower":0, "upper":255, "way":1, "incr":[30,10,1]},
			{"name":"sat_max", "value":225, "lower":0, "upper":255, "way":-1, "incr":[30,10,1]},
			{"name":"val_min", "value": 57, "lower":0, "upper":255, "way":1, "incr":[30,10,1]},
			{"name":"val_max", "value":205, "lower":0, "upper":255, "way":-1, "incr":[30,10,1]}
		],
		"size": [[5,40], [5,40]]
		},
		"2":{
		"cls":2,
		"name":"sk8",
		"algo":0,
		"spec":[
			{"name":"hue_min", "value":  0, "lower":0, "upper":255, "way":1, "incr":[30,10,1]},
			{"name":"hue_max", "value": 17, "lower":0, "upper":255, "way":-1, "incr":[30,10,1]},
			{"name":"sat_min", "value":117, "lower":0, "upper":255, "way":1, "incr":[30,10,1]},
			{"name":"sat_max", "value":195, "lower":0, "upper":255, "way":-1, "incr":[30,10,1]},
			{"name":"val_min", "value": 47, "lower":0, "upper":255, "way":1, "incr":[30,10,1]},
			{"name":"val_max", "value":128, "lower":0, "upper":255, "way":-1, "incr":[30,10,1]}
		],
		"size": [[15, 45], [30, 90]]
	}}

	s = dump(example_model)
	print(f'dump\n{s}')

	s = format(example_model)
	print(f'\nformat\n{s}')

	fname = 'test_model.json'
	print(f'\nwrite to disk\n{example_model}')
	write(example_model, fname)

	t = read(fname)
	print(f'\nread back in\n{t}')

	initialize(t,'1')
	print(f'\ninitialize in place\n{t}')

if __name__ == '__main__':
	main()
