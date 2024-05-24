

import matplotlib.animation as animation 
import matplotlib.pyplot as plt 
import numpy as np 
import os
 
 
# creating a blank window 
# for the animation 
fig = plt.figure() 
axis = plt.axes(xlim =(-50, 50), 
                ylim =(-50, 50)) 
 
line, = axis.plot([], [], lw = 2) 
 
# what will our line dataset 
# contain? 
def init(): 
    line.set_data([], []) 
    return line, 
 
# initializing empty values 
# for x and y co-ordinates 
xdata, ydata = [], [] 
 
print(f'parent {os.getpid()}')

# animation function 
def animate(i): 
    print(os.getpid())
    # t is a parameter which varies 
    # with the frame number 
    t = 0.1 * i 
     
    # x, y values to be plotted 
    x = t * np.sin(t) 
    y = t * np.cos(t) 
     
    # appending values to the previously 
    # empty x and y data holders 
    xdata.append(x) 
    ydata.append(y) 
    line.set_data(xdata, ydata) 
     
    return line, 
 
# calling the animation function     
anim = animation.FuncAnimation(fig, animate, 
                            init_func = init, 
                            frames = 500,
                            interval = 20, 
                            blit = True) 
 
anim.save('growingCoil.mp4', writer = 'ffmpeg', fps = 30) 
