'''
cls:1, values: [25, 76, 119, 255, 101, 196, 11, 27, 11, 27]


cls:2, led, values: [153, 4, 8, 4, 8]

cls:2, donut  gray 173, 143, 119, values: [153, 4, 8, 4, 8]

'''

import numpy as np
a = [
[132, 23, 33, 23, 33],  # 95, 1 
[132, 23, 33, 23, 33],  # 96, 1 
[168, 23, 33, 23, 33],  # 97, 1 
]

b = np.array(a)

c = np.mean(b[:,0])

print(c)

breakpoint()
