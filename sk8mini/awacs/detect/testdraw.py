' testdraw.py - test the draw library '

import cv2
import draw

folder = '/home/john/media/webapps/sk8mini/awacs/photos/training/'
base = '00001'

truth = [
	[1, 533, 517, 20, 20, 0], 
	[1,  72, 512, 31, 24, 0], 
	[1, 186, 407, 27, 21, 0], 
	[1, 405, 399, 21, 21, 0], 
	[1, 287, 288, 25, 24, 0], 
	[1, 177, 184, 27, 25, 0], 
	[1, 392, 172, 29, 24, 0], 
	[1, 526,  42, 24, 24, 0], 
	[2, 496, 294,  8, 12, 0], 
	[2, 458, 290, 14, 10, 0], 
	[2, 482, 288,  8, 10, 0], 
	[2, 500, 265,  7, 11, 0], 
	[2, 461, 261,  9, 11, 0], 
	[3, 471, 279, 30, 27, 0] 
]
label = [
	[1,530,514,25,24,542,526,24],
	[1, 71,513,31,25, 86,525,28],
	[1,185,406,26,22,198,417,24],
	[1,406,398,22,23,417,409,22],
	[1,470,298,31,20,485,308,25],
	[1,286,287,25,27,298,300,26],
	[1,174,183,29,27,188,196,28],
	[1,394,173,28,23,408,184,25],
	[1,527, 42,27,26,540, 55,26],
	[3,471,279,29,25,485,291,27],
]

options_truth = {
	"color_normal": (  0,255,  0),    # (B, G, R)
	"color_selected": (255,  0,  0),    # (B, G, R)
	"thickness_normal": 2,
	"thickness_selected": 4,
	"shape": "circle"
}
options_label = {
	"color_normal": (128,128,255),    # (B, G, R)
	"color_selected": (  0,  0,255),    # (B, G, R)
	"thickness_normal": 2,
	"thickness_selected": 4,
	"shape": "rectangle"
}

def main():
	global label
	fname = folder + base + '.jpg'
	image = cv2.imread(fname, cv2.IMREAD_UNCHANGED)
	#image = draw.createImage()
	selected = 3
	image = draw.draw(image, label, options_label, selected)
	image = draw.draw(image, truth, options_truth, selected)
	draw.showImage(image)

if __name__ == '__main__':
	main()

