import time
def cmd(x,y,z,w):
	scmd = f'rc {x} {y} {z} {w}'
	print(z)		

def takeoff():
	for z in list(range(0,80)) + list(range(80,50,-1)):
		cmd(0,0,z,0)
		time.sleep(0.03)

locals()['takeoff']()
