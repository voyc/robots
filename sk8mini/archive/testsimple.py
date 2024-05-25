
import matplotlib.pyplot as plt
import logging

logging.getLogger('').setLevel(logging.DEBUG)

def on_press(event):
	print('press', event.key)
	if event.key == 'left':
		print('turn left')
	if event.key == 'right':
		print('turn right')
	if event.key == 'up':
		print('go straight')

fig, ax = plt.subplots()
fig.canvas.mpl_connect('key_press_event', on_press)
plt.show()

