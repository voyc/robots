'''
testtkinter.py - test the tkinter library

There are several GUI packages for Python.  tkinter is the one that is included by default.
tkinter implements widgets, layout, and events

widget layout methods:
	pack() - ok for one-column or one-row layouts
	place() - specify x,y pixel coordinates
	grid() - place widgets relative to one another in columns and rows

ttk - themed widgets, newer styled widgets that override the older widgets

12 widgets found in both tk and ttk:
	Button
	Checkbutton
	Entry
	Frame - container
	Label - static text or image
	LabelFrame - container with border and title, example: groupbox of radio buttons
	Menubutton
	PanedWindow
	Radiobutton
	Scale - slider
	Scrollbar
	Spinbox

6 widgets found only in ttk
	Combobox
	Notebook
	Progressbar
	Separator
	Sizegrip
	Treeview

2 widgets found only in tk
	Canvas - drawing lines, polygons, etc.
	PhotoImage - an image object


images
	a PhotoImage object is NOT a numpy array, unlike other python image libraries
	supported formats: GIF, PGM, PPM, PNG (as of Tkinter 8.6)
	the Pillow library has a Tkinter-compatible PhotoImage widget located in the PIL.ImageTk module.

	an image can be placed in a Label or in a Canvas


	PhotoImage 


To support other file formats such as JPG, JPEG, or BMP, you can use an image library such as Pillow to convert them into a format that the PhotoImage widget understands.


import PIL
	this command might load either PIL or Pillow
	Python Image Library (PIL), comes with python3
	Pillow, a new drop-in replacement for PIL, must be installed with PIP

format - file extension or None if not read from a file
mode - RGB, L, P, RGBA, LA, PA
size - (width, height)

pixel depth, or number of channels or bands, for each mode:
	RGB  3
	P    1 Palette, 256 colors with separate matrix for palette
	L    1 Luminance, grayscale
	RGBA 4 plus alpha channel
	PA   2
	LA   2

im = Image.open(filename)
im.convert('RGB')
im.getchannel(0)

'''
import tkinter as tk
from tkinter import ttk 
from PIL import ImageTk, Image
import cv2
import numpy as np

def pngFromJpg(jpg):
	bc,gc,rc = cv2.split(jpg)
	w,h,_ = jpg.shape
	ac = np.ones((w,h), np.uint8)
	png = cv2.merge([rc,gc,bc,ac])
	return png

def _photo_image(image: np.ndarray):
	height, width = image.shape[:2]
	data = f'P5 {width} {height} 255 '.encode() + image.astype(np.uint8).tobytes()
	return tk.PhotoImage(width=width, height=height, data=data, format='PPM')


window = tk.Tk()
window.title("GUI")
window.geometry("1200x600")
labelTitle = ttk.Label(window, text='Hello World!')
labelTitle.grid(column=1,row=1)

fname = 'photos/20240109-174051/00874.jpg'
jpg = cv2.imread(fname)
png = pngFromJpg(jpg)

#cv2.imwrite("temp.png", png)

#canvas = tk.Canvas( window, width = 600, height = 600)      
#canvas.pack()      

#img = PhotoImage(file='images/sasuke.png')      
#img = tk.PhotoImage(data=png)      
#canvas.create_image( 10, 10, anchor=tk.NW, image=png)      


#img = ImageTk.PhotoImage(Image.open(fname))
#img = ImageTk.PhotoImage(png)
#img = Image.fromarray(png)

img = _photo_image(jpg)





labelText = ttk.Label(window, text='Goodbye')
labelText.grid(column=3,row=1)



canvas = tk.Canvas(window, width=600, height=400, bg='white')
canvas.grid(column=3, row=1)

print(jpg.shape)

img = Image.fromarray(jpg)
print(img.format)
print(img.mode)
print(img.size)

gray = img.convert('L')

print(gray)
labelImg = ttk.Label(window, image=gray)
labelImg.grid(column=2, row=1, rowspan=2)



def empty():
	pass



#while True:
#	empty()
#	window.update_idletasks()
#	window.update()

btnquit = ttk.Button(window, text="Quit", command=window.destroy)
btnquit.grid(column=1,row=2)
window.mainloop()
