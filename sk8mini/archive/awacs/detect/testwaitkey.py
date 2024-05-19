import cv2
import sys

cv2.imshow(sys.argv[1], cv2.imread(sys.argv[1]))
while True:
	res = cv2.waitKey(10000)
	print(res, res & 0xFF)
	#print('You pressed %d (0x%x), LSB: %d (%s)' % (res, res, res % 256,
	#	repr(chr(res%256)) if res%256 < 128 else '?'))
	if res == ord('q'):  break
	if res == -1: break

# waitKey() does not return when window is closed
# the program appears to hang until the timeout
# therefore, we use 10000 instead of 0
