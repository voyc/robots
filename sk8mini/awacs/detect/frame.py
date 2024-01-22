'''
frame.py - frame file management library
'''
import os

def fqjoin(path, base, ext):
	if ext[0] != '.':
		ext = '.' + ext
	return os.path.join(path,base+ext)

def getFrameList(path, nozero=True):
	flist = []
	for filename in os.listdir(path):
		fnum, ext = os.path.splitext(filename)
		if ext == '.jpg':
			flist.append(fnum)
	slist = sorted(flist)
	if nozero and slist[0] == '00000':
		slist.pop(0)
	return slist

