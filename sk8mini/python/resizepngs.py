#import os
#dirname = '/home/john/media/webapps/sk8mini/awacs/photos/20240703-080355/'
#cwd = os.getcwd()
#os.chdir(dirname)
#for filename in os.listdir('*.png'):
#	print(filename)


import glob
from PIL import Image

path = '/home/john/media/webapps/sk8mini/awacs/photos/20240703-080355/*.png'
for filename in glob.glob(path):
	im = Image.open(filename)
	w,h = im.size
	if w != 600:
		print(filename, w, h)
		#resized_img = im.resize((600, 600))
		#resized_img.save(filename)
	
	#if w == 923:
	#	resized_img = im.resize((600, 600))
	#	resized_img.save(filename)
