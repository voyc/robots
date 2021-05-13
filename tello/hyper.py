# hyperbola.py

import numpy as np
import matplotlib.pyplot as plt

x = np.array([20,40,90,110,130,150,170,190,200,400,600,800,1000,1500,2000])
y = np.array([24.2083,13.5833,10.6667,5.5000,4.7917,4.2500,3.8750,3.3333,2.2525,1.3460,0.8928,0.7071,0.6389,0.5143,0.4476])
plt.scatter(x, y)

k = 521
y1 = k/x
plt.plot(x, y1)
plt.show()
print(y1)

best_k = 500
least_sse = 10000
for k in range(500,550):
	y1 = k/x
	sse = sum((y - y1) ** 2)
	if sse < least_sse:
		least_sse = sse
		best_k = k
print(best_k)
print(least_sse)

'''
Wikipedia gives this equation  y = k/x
The Dutch fellow on youtube uses this equation: y=(m*x)/(k+x)

26.05       
13.025       
5.78888889  
4.73636364  
4.00769231  
3.47333333
3.06470588  
2.74210526  
2.605       
1.3025      
0.86833333  
0.65125
0.521       
0.34733333  
0.2605

'''

