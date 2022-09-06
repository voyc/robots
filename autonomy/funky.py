'''
funky.py
replacement for FuncAnimation(), using pyplot.ion() and pause()
see https://stackoverflow.com/questions/28269157/plotting-in-a-non-blocking-way-with-matplotlib
'''
import numpy as np
import matplotlib.pyplot as plt  

def FunkAnimation(looper, numframes, fps):  
	delay = fps/1000
	plt.ion()
	plt.show()
	for i in range(numframes):
		looper(i)
		plt.pause(delay)

def main():
	global bow, stern, incr, skateline
	skateline = plt.gca().scatter([0,0,0,0,0],[0,0,0,0,0], c=['r','r','r','r','b'])
	bow = np.array([1000,1000])
	stern = np.array([1200,1200])
	incr = np.array([20,20])
	
	color = 'black'
	plt.xlim(0,4000)
	plt.ylim(0,4000)
	plt.autoscale(False)
	plt.gca().set_aspect('equal', anchor='C')
	plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
	plt.gca().spines['bottom'].set_color(color)
	plt.gca().spines['top'].set_color(color)
	plt.gca().spines['left'].set_color(color)
	plt.gca().spines['right'].set_color(color)
	
	FunkAnimation(animate, 50, 20)
	
def animate(framenum):
	global bow,stern,incr, skateline
	bow += incr
	stern += incr
	points = drawSkate(bow,stern,5)
	skateline.set_offsets(points) # FuncAnimation does the drawing

def drawSkate(bow, stern, n):
	diff = (bow - stern) / n
	points = []
	for i in range(n): points.append(stern + (diff * i))
	return points
	
if __name__ == '__main__':
	main()
