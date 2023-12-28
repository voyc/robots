'''
detection.py - detection management library

a detection is a two-dimensional list of integers, 
one row for each detected object in an image
the first column is the classifier
the next four columns represent the bounding box of the object, l,t,w,h
this list is assumed to have been sorted, ala sorted(detect)

a detection object is stored in a .csv file
example filenames:
00001.jpg - the image
00001_detect.csv - the detection file
00001_train.csv - a perfected detection file, used for training
'''

import csv

def read(fname):
	detection = []
	with open(fname, 'r') as f:
		reader = csv.reader(f)
		for srow in reader:
			irow = []
			for cell in srow:
				irow.append(int(cell))		
			detection.append(irow)
		return detection

def write(detection, fname):
	with open(fname, 'w') as f:
		wr = csv.writer(f)
		wr.writerows(detection)

def format(detection):
	s = ''
	for row in detection:
		s += str(row)+'\n'
	return s

# ------------------- unit test ------------------------- #

def main():
	example_detection = [
		[1, 533, 517, 20, 20],
		[1, 186, 407, 27, 21],
		[2, 482, 288,  8, 10],
	]
	s = format(example_detection)
	print(f'format\n{s}')

	fname = 'test.csv'

	print('write to file')
	print(example_detection)
	write(example_detection, fname)

	print('read back in')
	t = read(fname)
	print(t)

if __name__ == '__main__':
	main()
