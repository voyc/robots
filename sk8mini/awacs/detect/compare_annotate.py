import numpy as np
import copy


# one training set and three tests
trainfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/00095_trained.csv'
equalfname = '/home/john/media/webapps/sk8mini/awacs/photos/training/00095_annot.csv'
shortfname = 
extrafname =

# also needed
# a program to dislay image with overlaid annotations
# choice of box or ring
# keyboard control to nudge each object and rewrite the training set 


tt = [1, 527, 43, 26, 25, 540, 55, 25]
ta = [1, 529, 45, 22, 22, 540, 56, 22]

penalty_missing = 1000
penalty_extra = 900

c=0
l=1
t=2
w=3
h=4
x=5
y=6
r=7
m=8
e=9


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
			#print(trow)
	return tlist

def printAnnotate(annot):
	for a in annot:
		print(a)
	print()

# calc mean squared error using numpy vector math
def mse(predicted, actual):
	actual = np.array(actual)
	predicted = np.array(predicted)
	differences = np.subtract(actual, predicted)
	squared_differences = np.square(differences)
	return squared_differences.mean()

# compare x,y,r of two objects, and return mse
def score(t,a):
	return int(mse(t[x:r+1], a[x:r+1]))


# match each train object to one annot object, by scoring all possible pairs
# return a copy of train with two additional columns: the index and mse of the matched object
def match(train,annot):
	mtrain = copy.deepcopy(train)
	for t in mtrain:
		t.append(0)
		t.append(penalty_missing)
		ndx = 0
		for a in annot:
			ndx += 1 # 1-based index
			if a[c] == t[c]:
				mse = score(t,a)
				if mse < t[e]: 
					t[m] = ndx
					t[e] = mse

	# replace dupes
	strain = sorted(mtrain, key=lambda a: [a[m], a[e]])	
	save = -1
	for s in strain:
		if save == s[m]:
			s[m] = 0 # no match
			s[e] = penalty_missing
		else:
			save = s[m]

	# total errors for all objects in train, matched and unmatched 
	error = 0
	for t in mtrain:
		error += t[e]

	# add errors for all unmatched objects left oveer in annot
	diff = len(annot) - len(train)
	if diff > 0:
		penalty = diff * penalty_extra
		say = f'extra:{diff}, penalty:{penalty}')
		error += penalty

	print(f'train count:{len(train)}') 
	print(f'annot count:{len(annot)}') 
	print(say)
	
	mean = int(error / len(train))
	return error, mtrain

def main():
	train = readAnnotate(trainfname)
	annot = readAnnotate(annotfname)
	
	train = sorted(train)
	annot = sorted(annot)
	
	printAnnotate(train)
	printAnnotate(annot)
	
	# array of cls values in the train
	clsScore = {}
	for t in train:
		clsScore[t[c]] = 0
	print(clsScore)
	print()
	
	# example with more annot than train - extra objects
	error, matched = match(train,annot)
	print(error)
	printAnnotate(matched)
	
	# example with more train than annot - missing objects
	error, matched = match(annot, train)
	print(error)
	printAnnotate(matched)

	# error is the same in both examples.  
	# because the score for missing an object is the same as that for an extra
	
	quit()

main()

