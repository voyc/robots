import os
dirname = '/home/john/media/webapps/sk8mini/awacs/photos/20240531-132843_tight-circle-port'
dirname = '/home/john/media/webapps/sk8mini/awacs/photos/20240531-133001_straight-23'
dirname = '/home/john/media/webapps/sk8mini/awacs/photos/20240531-133102_straight-43'
dirname = '/home/john/media/webapps/sk8mini/awacs/photos/20240531-133204_straight-3' 


cwd = os.getcwd()
os.chdir(dirname)
for filename in os.listdir():
	s = os.path.splitext(filename)[0]
	ext = os.path.splitext(filename)[1]
	f = float(s)
	newname = f'{f:.2f}'.replace('.','_') + ext
	os.rename(filename, newname)
