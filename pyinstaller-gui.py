#!/usr/bin/python
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# Tkinter interface to PyInstaller.
#


import sys
import subprocess

# In Python 3 module name is 'tkinter'
try:
    from tkinter import *
    from tkinter.ttk import *
    import tkinter.filedialog as filedialog
except ImportError:
    from Tkinter import *
    from ttk import *
    import tkFileDialog as filedialog


class PyInstallerGUI:

    def __init__(self):
        root = Tk()
        root.title("PyInstaller GUI")

        main = Frame(root)
        main.pack()

        self.fin = StringVar()
        getFileButton = Button(main, text="Script to bundle ")
        getFileButton.bind("<Button>", self.GetFile)
        getFileButton.grid(row=0, column=0)
        self.fileinEntry = Entry(main, textvariable=self.fin)
        self.fileinEntry.grid(row=0, column=1)

        self.fout = StringVar()
        getOutputButton = Button(main, text="Output directory")
        getOutputButton.bind("<Button>", self.GetOutput)
        getOutputButton.grid(row=1, column=0)
        self.fileoutEntry = Entry(main, textvariable=self.fout)
        self.fileoutEntry.grid(row=1, column=1)

        self.icon = StringVar()
        if sys.platform.startswith('win') or sys.platform == 'darwin':
            getIconButton = Button(main, text="     Icon to use     ")
            getIconButton.bind("<Button>", self.GetIcon)
            getIconButton.grid(row=2, column=0)
            self.icondirEntry = Entry(main, textvariable=self.icon)
            self.icondirEntry.grid(row=2, column=1)

        fr2 = Frame(main, borderwidth=2, relief="ridge")
        fr2.grid(row=3, column=0, columnspan=2, ipadx=10, ipady=10)
        self.filetype = self.make_checkbutton(fr2, "One File Package")
        self.ascii = self.make_checkbutton(fr2, "Do NOT include decodings")
        self.debug = self.make_checkbutton(fr2, "Use debug versions")
        if sys.platform.startswith('win'):
            self.noconsole = self.make_checkbutton(fr2,
                                                   "No console (Windows only)")
        else:
            self.noconsole = IntVar()
        if not sys.platform.startswith('win'):
            self.strip = self.make_checkbutton(fr2,
                                               "Strip the exe and shared libs")
        else:
            self.strip = IntVar()

        okayButton = Button(main, text="Okay   ")
        okayButton.bind("<Button>", self.makePackage)
        okayButton.grid(row=4, column=0)

        cancelButton = Button(main, text="Cancel")
        cancelButton.bind("<Button>", self.killapp)
        cancelButton.grid(row=4, column=1)

        self.center(root)
        root.mainloop()

    def center(self, window):
        window.update_idletasks()
        w, h = window.winfo_width(), window.winfo_height()
        ws, hs = window.winfo_screenwidth(), window.winfo_screenheight()
        x, y = (ws // 2) - (w // 2), (hs // 2) - (h // 2)
        window.geometry('{}x{}+{}+{}'.format(w, h, x, y))

    def killapp(self, event):
        sys.exit(0)

    def make_checkbutton(self, frame, text):
        var = IntVar()
        widget = Checkbutton(frame, text=text, variable=var)
        widget.grid(sticky="w")
        return var

    def makePackage(self, event):
        commands = [sys.executable, 'pyinstaller.py']
        if self.filetype.get():
            commands.append('--onefile')
        if self.ascii.get():
            commands.append('--ascii')
        if self.debug.get():
            commands.append('--debug')
        if self.noconsole.get():
            commands.append('--noconsole')
        if self.strip.get():
            commands.append('--strip')
        if self.fout.get():
            commands.append('--distpath={}'.format(self.fout.get()))
        if self.icon.get():
            commands.append('--icon={}'.format(self.icon.get()))
        commands.append(self.fin.get())
        retcode = subprocess.call(commands)
        sys.exit(retcode)

    def GetFile(self, event):
        file = filedialog.askopenfilename()
        if file:
            self.fileinEntry.delete(0, 'end')
            self.fileinEntry.insert(0, file)

    def GetOutput(self, event):
        directory = filedialog.askdirectory()
        if directory:
            self.fileoutEntry.delete(0, 'end')
            self.fileoutEntry.insert(0, directory)

    def GetIcon(self, event):
        file = filedialog.askopenfilename()
        if file:
            self.icondirEntry.delete(0, 'end')
            self.icondirEntry.insert(0, file)


if __name__ == "__main__":
    raise SystemExit("Please use just 'pyinstaller.py'. Gui is not maintained.")
    try:
        app = PyInstallerGUI()
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
