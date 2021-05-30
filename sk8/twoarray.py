
x = [23,46,26,293]
y = [1,5,9,27,57,297,4,72,499,23]
z = []
for i in x:
	for j in y:
		e = i - j
		se = e**2
		z.append((se,i,j))
z.sort()
num = len(x)
enum = len(y) - num
a = z[0:num]
print(*a, sep='\n')
print('enum', enum)
print(*z, sep='\n')

'''
no, it's not fair to compare and take the best ones,
because the target comparison is not available in real life.
you have to have a repeatable algorithm

take the largest n
take the first one
combine all into one
combine all that fall within a percentage distance
	blur sort of does this
'''
