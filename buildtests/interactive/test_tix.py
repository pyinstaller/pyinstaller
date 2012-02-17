
import Tix as tix

root = tix.Tk()
root.title("Test for TiX")

tix.Label(text="Press <ESC> to exit").pack()
tix.DirList(root).pack()
tix.Button(root, text="Close", command=root.destroy).pack()
root.bind("<Escape>", lambda x: root.destroy())

tix.mainloop()
