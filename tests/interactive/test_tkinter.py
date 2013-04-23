# -*- coding: utf-8 -*-

from Tkinter import *

root = Tk()
root.title("Test for Tkinter")
root.bind("<Escape>", lambda x: root.destroy())

Label(text="Press <ESC> to exit. Some non ascii chars: řčšěíáŘ").pack()
Button(root, text="Close", command=root.destroy).pack()

root.mainloop()
