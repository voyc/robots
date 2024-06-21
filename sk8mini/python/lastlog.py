#!/usr/bin/python3 

'''
lastlog.py
'''

import glob
basedir = 'photos/2024*/'
dirs = glob.glob(basedir)
lastdir = list(reversed(sorted(dirs)))[0]
print(lastdir)

from tkinter import Tk # in Python 2, use "Tkinter" instead 
r = Tk()
r.withdraw()
r.clipboard_clear()
r.clipboard_append(lastdir)
r.update() # now it stays on the clipboard after the window is closed
r.destroy()
