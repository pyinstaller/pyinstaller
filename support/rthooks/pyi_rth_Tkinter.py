import os
import sys


basedir = sys._MEIPASS


tcldir = os.path.join(basedir, '_MEI', 'tcl')
tkdir = os.path.join(basedir, '_MEI', 'tk')


# Directories with .tcl files.
os.environ["TCL_LIBRARY"] = tcldir
os.environ["TK_LIBRARY"] = tkdir
