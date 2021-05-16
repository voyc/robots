# hyperbola.py
# for source of input data, see agl.ods

import numpy as np
import matplotlib.pyplot as plt

x = np.array([20,40,90,110,130,150,170,190,200,400,600,800,1000,1500,2000])
y = np.array([24.2083,13.5833,10.6667,5.5000,4.7917,4.2500,3.8750,3.3333,2.2525,1.3460,0.8928,0.7071,0.6389,0.5143,0.4476])

y = np.array([1,100,200,300,400,500,600,700,800,900,1000,1500,2000])

# spot
x = np.array([34,7.2812625,4.5937649375,3.2499975,2.6562375,2.2812525,1.81251,1.7187525,1.499985,1.4375025,1.3125,0.9374849375,0.7187475])
# mix
x = np.array([34,7.2812625,4.5937649375,3.2499975,2.45953310714286,2.05761809285714,1.63514153571429,1.51660756071429,1.33174421071429,1.2267027,1.14197513214286,0.790346161607143,0.605824775])

plt.scatter(x, y)

best_k = 1143
least_sse = 10000000
for k in range(1000,1500):
	y1 = k/x
	sse = sum((y - y1) ** 2)
	if sse < least_sse:
		least_sse = sse
		best_k = k
print(best_k)
print(least_sse)

k = best_k
y1 = k/x
print(y1)
plt.plot(x, y1)
plt.show()

print(*y1, sep='\n')

'''
Wikipedia gives this equation  y = k/x
The Dutch fellow on youtube uses this equation: y=(m*x)/(k+x)

based on 640 pxl width images
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

based on 960 pxl width images
36.3125
20.3750
16.0000
8.2500
7.1875
6.3750
5.8125
5.0000
3.3788
2.0190
1.3392
1.0607
0.9584
0.7714
0.6714

'''

