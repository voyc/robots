''' sim.py 
https://www.geeksforgeeks.org/using-matplotlib-for-animations/


t = 0.1 second (10 fps)
speed = 20   # constant speed
nav loop:
	detect current position of sk8
	plot next position at current heading and speed 
	calc variance from desired position
	if too far out, emergency stop
	calc new desired heading to correct course 
		bearing = direction to next destination
		relative bearing = heading - bearing
		steering angle proportional to relative bearing
	request new steering angle

sim loop:
	plot next position at current heading, steering, and speed 
	for testing, apply random drift
	move to next position
	
for now, do straight lines, then add arcs, steering
when wheels are turned, heading is in constant change
steering angle

parameters
	delay between steering request and heading change
	steering proportion to relative bearing

variables

algorithms
	nav - set steering angle
	steering stability - minimal steering, avoid over correction weaving
	simulate drift, random or otherwise

'''

from matplotlib import pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation 
   
arena_spec = {
	'w':4000,
	'h': 4000,
	'title': 'Arena'
}

# initializing a figure in which the graph will be plotted
fig = plt.figure() 
   
# initializing a line variable
line, = plt.gca().plot([], [], lw = 3) 
begin = 0
end = 200
girth = 20
speed = 15
   

path = []

#line, A, B, entry
#arc, theta1, theta2, wise
#cone, entry, exit, 


def init(): 
	# called once before first frame
	return line,
   
def animate(frame):
	# called once for every frame
	global line, begin, end, girth
	x = np.linspace(begin, end, girth)

	y = x * 2
	line.set_data(x, y)
  
	begin += speed
	end += speed
	return line, # because blit=True, return a list of artists

   
anim = FuncAnimation(fig, animate, init_func=init, frames=range(1,200), interval=20, blit=True)
  
plt.xlim(0,arena_spec['w'])
plt.ylim(0,arena_spec['h'])
plt.autoscale(False)
plt.gca().set_aspect('equal', anchor='C')
plt.tick_params(left=False, right=False, labelleft=False, labelbottom= False, bottom=False)
plt.gca().spines['bottom'].set_color('cyan')
plt.gca().spines['top'].set_color('cyan')
plt.gca().spines['left'].set_color('cyan')
plt.gca().spines['right'].set_color('cyan')
plt.show()

#anim.save('continuousSineWave.mp4', writer = 'ffmpeg', fps = 30)
