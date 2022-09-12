'''
funky.py
replacement for FuncAnimation(), using pyplot.ion() and pause()
see https://stackoverflow.com/questions/28269157/plotting-in-a-non-blocking-way-with-matplotlib

two alternative methods for saving video via ffmpeg: pipe or temporary disk files
'''
import numpy as np
import matplotlib.pyplot as plt  
import subprocess as sp

tempname = 'tempfunk'
videodir = 'videos'

def catVideo(fout):
	sp.run(['ffmpeg', '-v', 'warning', '-i', f'{tempname}%04d.png', '-y', f'{fout}.mp4'])
	sp.run(f'rm {tempname}????.png', shell=True)

def startVideo(fout):
	command = ['ffmpeg', '-v', 'warning', '-i', '-', '-y', f'{fout}.mp4']
	pipe = sp.Popen(command, stdin=sp.PIPE)
	return pipe

def FunkAnimationPipe(looper, numframes, fps, savevideo=None):  
	delay = fps/1000
	plt.ion()
	plt.show()
	fig = plt.gcf()

	if savevideo:
		pipe = startVideo(savevideo)

	running = True
	def onpress(event):
		nonlocal running
		if event.key == 'q': running = False
	fig.canvas.mpl_connect('key_press_event', onpress)
	for framenum in range(numframes):
		looper(framenum)
		if savevideo:
			fig.canvas.print_png(pipe.stdin)
		plt.pause(delay)
		if not running: break
	pipe.stdin.close()
	pipe.wait()

def FunkAnimationDisk(looper, numframes, fps, savevideo=None):  
	delay = fps/1000
	plt.ion()
	plt.show()

	running = True
	def onpress(event):
		nonlocal running
		if event.key == 'q': running = False
	plt.gcf().canvas.mpl_connect('key_press_event', onpress)
	for framenum in range(numframes):
		looper(framenum)
		if savevideo:
			plt.savefig( f'{tempname}{framenum:04d}.png')
		plt.pause(delay)
		if not running: break

	if savevideo:
		catVideo(savevideo)

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
	
	#FunkAnimationDisk(animate, 100, 20, savevideo='funkymovie')
	FunkAnimationPipe(animate, 100, 20, savevideo='funkymovie')
	
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
