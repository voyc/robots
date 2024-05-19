'''
simscore.py - compare latest label to ground truth
'''
import argparse

import frame as frm
import score as scr
import label as lbl

gargs = None
gframendx = 0
gframelist = []

def getFrameNum():
	global gframendx, gframelist
	if gframendx == 0:
		gframelist = frm.getFrameList(gargs.idir)
	if gframendx >= len(gframelist):
		return None
	fnum = gframelist[gframendx]
	gframendx += 1
	return fnum

def looper():
	framecnt = 0
	totscore = 0
	hierror = 0
	while True:
		fnum = getFrameNum()
		if fnum is None:
			break;
		framecnt += 1

		# read two label files
		labelset = lbl.read(frm.fqjoin(gargs.idir, fnum, gargs.ilabelsufx))
		truthset = lbl.read(frm.fqjoin(gargs.idir, fnum, gargs.itruthsufx))

		# match
		error, pscore, clscores, scoredlabelset =  scr.scoreLabelsAgainstTruth(truthset, labelset)

		print(pscore, clscores, scoredlabelset)

		#if gargs.otruthsufx:
		#	label.write(scoredlabel)
		totscore += pscore
		if error > hierror:
			hierror = error

	avgscore = totscore / framecnt
	return avgscore, hierror

def main():
	global gargs
	defidir = 'photos/20231216-092941/'  # day
	defilabelsufx = 'label.csv'
	defitruthsufx = 'truth.csv'

	# get command-line parameters 
	parser = argparse.ArgumentParser()
	parser.add_argument('-id' ,'--idir'                ,default=defidir      ,help='input folder'        )
	parser.add_argument('-il' ,'--ilabelsufx'          ,default=defilabelsufx,help='suffix of input label file'   )
	parser.add_argument('-it' ,'--itruthsufx'          ,default=defitruthsufx,help='suffix of input truth file'   )
	gargs = parser.parse_args()	# returns Namespace object, use dot-notation

	avgscore, hierror = looper()
	print(avgscore, hierror)

if __name__ == '__main__':
	main()

