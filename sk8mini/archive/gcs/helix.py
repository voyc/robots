'''helix.py'''
from plothelper import *
from mpl_toolkits.mplot3d import Axes3D

title = 'Helix'

fig = plt.figure()
ax = fig.add_subplot(121, projection='3d')

# Plot a helix along the z-axis
n = 1000
theta_max = 8 * np.pi
theta = np.linspace(0, theta_max, n)
z = theta
x =  np.sin(theta)
y =  np.cos(theta)
ax.plot(x, y, z, 'b', lw=2)

# An line through the centre of the helix
#ax.plot((-theta_max*0.2, theta_max * 1.2), (0,0), (0,0), color='k', lw=2)

# sin/cos components of the helix (e.g. electric and magnetic field
# components of a circularly-polarized electromagnetic wave
#ax.plot(x, y, 0, color='r', lw=1, alpha=0.5)
#ax.plot(x, [0]*n, z, color='m', lw=1, alpha=0.5)

# Remove axis planes, ticks and labels
#ax.set_axis_off()

#formatgraph(False)
#savegraph(title)
#plt.show()


title = 'circle in cartisean coordinates'

# x**2 + y**2 = r**2  # cartesian equation for a circle, with r = radius

theta = np.linspace(0, 2*np.pi, 100)  # 100 points from 0 to 2pi
r = np.sqrt(10)  # radius

x = r*np.cos(theta)
y = r*np.sin(theta)
z = theta

#fig, ax = plt.subplots(1)
#ax.plot(x,y)
#ax.set_aspect(1)
#plt.show()

ax = fig.add_subplot(122, projection='3d')
ax.plot(x,y,z,'b')
#ax.plot(x, y, z, 'b', lw=2)
plt.show()


