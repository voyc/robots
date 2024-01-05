'''
testrealtime.py - test the way detectObjects will be called in realtime

'''
import cv2

import model as mod
import detect
import label as lab


#--------------- main loop ----------------------------------------# 

def main():

	image_folder = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
	image_fname = '00095.jpg'
	model_fname = '/home/john/media/webapps/sk8mini/awacs/photos/training/loop/model.json'

	# read model
	model = mod.read(model_fname)

	# read image
	img = cv2.imread(image_folder+image_fname, cv2.IMREAD_UNCHANGED)

	labels = []
	for m in model:
		label = detect.detectObjects(img, model, m)
		labels += label

	print(labels)

	slabels = lab.format(labels, 'realtime')

	print(slabels)

if __name__ == "__main__":
	main()
