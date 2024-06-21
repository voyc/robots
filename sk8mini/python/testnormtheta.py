'''
testnormtheta.py

see:
https://docs.google.com/spreadsheets/d/1uIcCr-msArC0PO4cTDux3zJk9BW8KO1s80gbWmK7pwA/edit#gid=1070382928
normalize_thetas.xcf

all numbers are theta - 0 to 6.28 ccw around the circle starting from right horizontal
'''

import numpy as np

def normalizeTheta(tfrom, tto, tat, rdir):
	tcirc = 6 # 2*np.pi
	if rdir == 'ccw':
		ntat = (tat - tfrom) % tcirc
		ntto = (tto - tfrom) % tcirc
	elif rdir == 'cw':
		ntat = tcirc - ((tat - tfrom) % tcirc)
		ntto = tcirc - ((tto - tfrom) % tcirc)
	if ntat > 5.5:
		ntat = 0.001
	return ntat, ntto

testcases = [
	{'rdir':'ccw', 'case':1, 'from':0.5, 'at':1.5, 'to':2.5},
	{'rdir':'ccw', 'case':2, 'from':5.5, 'at':0.5, 'to':1.5},
	{'rdir':'ccw', 'case':3, 'from':4.5, 'at':5.5, 'to':0.5},
	{'rdir':'ccw', 'case':4, 'from':1.5, 'at':5.5, 'to':0.5},
	{'rdir':'ccw', 'case':5, 'from':1.5, 'at':1.6, 'to':3.9},
	{'rdir':'ccw', 'case':6, 'from':1.5, 'at':1.4, 'to':3.9},
	{'rdir':'cw',  'case':1, 'from':0.5, 'at':1.5, 'to':2.5},
	{'rdir':'cw',  'case':2, 'from':5.5, 'at':0.5, 'to':1.5},
	{'rdir':'cw',  'case':3, 'from':4.5, 'at':5.5, 'to':0.5},
	{'rdir':'cw',  'case':4, 'from':1.5, 'at':5.5, 'to':0.5},
	{'rdir':'cw',  'case':5, 'from':1.5, 'at':1.6, 'to':3.9},
	{'rdir':'cw',  'case':6, 'from':1.5, 'at':1.4, 'to':3.9},
]


print(f"rdir\tcase\tfrom\tat\tto\t|\tnat\tnto\tonmark")
for case in testcases:
	nat,nto = normalizeTheta(case['from'], case['to'], case['at'], case['rdir'])
	onmark = (nat > nto)
	print(f"{case['rdir']}\t{case['case']}\t{case['from']}\t{case['at']}\t{case['to']}\t|\t{nat}\t{nto}\t{onmark}")
