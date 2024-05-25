'''
testanimkeypress.py

animation
https://gist.github.com/parulnith/2a29f424126e1b313259310d8927bccb

keypress
https://matplotlib.org/stable/gallery/event_handling/keypress_demo.html
'''

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
 
# animation function 
def animate(i): 
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
 
def on_press(event):
    print('press', event.key)
    if event.key == 'left':
        print('90 degree turn to the left')

fig.canvas.mpl_connect('key_press_event', on_press)

plt.show()
#anim.save('growingCoil.mp4', writer = 'ffmpeg', fps = 30) 
