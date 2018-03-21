# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# In Python 3 module name is 'tkinter'
try:
    from tkinter import *
except ImportError:
    from Tkinter import *


root = Tk()
root.title("Test for tkinter")
root.bind("<Escape>", lambda x: root.destroy())

Label(text="Press <ESC> to exit. Some non ascii chars: řčšěíáŘ").pack()
Button(root, text="Close", command=root.destroy).pack()

root.mainloop()
