import os

dirout = '/home/john/sk8/bench/train'

def getNextFrameNum(dirname):
	filelist = os.listdir( dirname)
	hnum = 0
	for fname in filelist: 
		fbase = os.path.splitext(fname)[0]
		num = int(fbase) 
		if num > hnum:
			hnum = num
	hnum += 1
	return hnum

dirframeout = f'{dirout}/frame'
outframenum = getNextFrameNum(dirframeout)
print(outframenum)
