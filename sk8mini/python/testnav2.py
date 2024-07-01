'''
testnav2.py
'''


import nav

A = [100,100]
B = [200,200]
print( nav.distancePointFromLine(A,B, [150,160]))
print( nav.distancePointFromLine(A,B, [160,150]))

print(nav.isPointPastLine(A,B,[260,160]))


print(nav.reckonLine(A, 45, 100))

#print(nav.lengthOfArc( .2, 4.1, 10, 'cw'))
#print(nav.lengthOfArc( 4.1, .2, 10, 'cw'))

print()
print(nav.lengthOfArcTheta(  .2, 4.1, 'cw'))
print(nav.lengthOfArcTheta( 4.1, 2.0, 'cw'))
print(nav.lengthOfArcTheta(  .2, 4.1, 'ccw'))
print(nav.lengthOfArcTheta( 4.1, 2.0, 'ccw'))

print()
print(nav.lengthOfArc(  .2, 4.1, 'cw' , 10))
print(nav.lengthOfArc( 4.1, 2.0, 'cw' , 10))
print(nav.lengthOfArc(  .2, 4.1, 'ccw', 10))
print(nav.lengthOfArc( 4.1, 2.0, 'ccw', 10))

