' sortall.py - sort all csv files in specified folder'
import os

ifolder = '/home/john/media/webapps/sk8mini/awacs/photos/training/test/test/'

def readAnnotate( fname):
	tlist = []
	with open(fname, 'r') as f:
		a = f.read()
		lines = a.split('\n')
		for line in lines:
			if line == '':
				break;
			row = line.split(', ')
			trow = list(map(int,row))
			tlist.append(trow)
	return tlist

def writeAnnotate(annotate, fname):
	with open(fname, 'w') as f:
		for a in annotate:
			f.write( f'{a[0]}, {a[1]}, {a[2]}, {a[3]}, {a[4]}, {a[5]}, {a[6]}, {a[7]}\n')

def main():
	# loop all csv files in folder
	for filename in os.listdir(ifolder):
		basename, ext = os.path.splitext(filename)
		if ext == '.csv': 
			train = readAnnotate(ifolder+filename)
			train = sorted(train)
			writeAnnotate(train, ifolder+filename)

main()
