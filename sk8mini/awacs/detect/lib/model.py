' model.py   library for model management'
import json
import logging

def read(fname):
	with open(fname, 'r') as f:
		model = json.load(f)
	logging.info(f'reading model from {fname}')
	print(model)
	return model

def write(model, fname):
	with open(fname, 'w') as f:
		f.write(json.dumps(model, indent=4))
	logging.info(f'writing model to {fname}')
	print(model)

def dump(model):
	logging.debug(json.dumps(model, indent=4))

def print(model):
	s = ''
	for n in model:
		s += f"{model[n]['cls']} {model[n]['name']}\n"
		for sp in model[n]['spec']:
			s += f"{sp}\n"
		s += f"model[n]['size']\n"
	logging.info(s)

def initialize(model, cls='all'):
	for n in model:
		modcls = model[n]
		if cls != 'all' and modcls != cls:
			continue
		for sp in modcls['spec']:
			if sp['way'] > 0:
				sp['value'] = sp['lower']
			else:
				sp['value'] = sp['upper']
	logging.debug(json.dumps(model, indent=4))


# model, fixed, read from disk, one model per folder
example_model = {
"1":{
"cls":1,
"name":"cone",
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

