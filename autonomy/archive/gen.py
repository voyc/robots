def infinite_sequence():
    num = 0
    while True:
        yield num
        num += 1


for i in infinite_sequence():
	if i > 10000:
		quit()
	print(i)
