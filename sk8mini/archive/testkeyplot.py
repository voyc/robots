'''
https://matplotlib.org/stable/gallery/event_handling/keypress_demo.html
'''

#import sys

import matplotlib.pyplot as plt
import numpy as np


def on_press(event):
    print('press', event.key)
#    sys.stdout.flush()
    if event.key == 'x':
        visible = xl.get_visible()
        xl.set_visible(not visible)
        fig.canvas.draw()
    if event.key == 'left':
        print('90 degree turn to the left')


# Fixing random state for reproducibility
np.random.seed(19680801)

fig, ax = plt.subplots()
fig.canvas.mpl_connect('key_press_event', on_press)
ax.plot(np.random.rand(12), np.random.rand(12), 'go')
xl = ax.set_xlabel('easy come, easy go')
ax.set_title('Press a key')
plt.show()
