# regress.py

import numpy as np
import matplotlib.pyplot as plt

X = [1, 5, 8, 10, 14, 18]
Y = [1, 1, 10, 20, 45, 75]

X = [20,40,90,110,130,150,170,190,200,400,600,800,1000,1500,2000]
Y = [24.2083,13.5833,10.6667,5.5000,4.7917,4.2500,3.8750,3.3333,2.2525,1.3460,0.8928,0.7071,0.6389,0.5143,0.4476]

# Train Algorithm (Polynomial)
degree = 3
poly_fit = np.poly1d(np.polyfit(X,Y, degree))

# Plot data
xx = np.linspace(0, 26, 2001)
plt.plot(xx, poly_fit(xx), c='r',linestyle='-')
plt.title('Polynomial')
plt.xlabel('X')
plt.ylabel('Y')
plt.axis([0, 25, 0, 2000])
plt.grid(True)
plt.scatter(X, Y)
plt.show()

# Predict price
print( poly_fit(12) )





y = k/x => k>0
smaller values of k make the curve sharper, closer to the origin

y=(m*x)/(k+x)

