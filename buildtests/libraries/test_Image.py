import sys
import os

import Image

# disable "leaking" the installed version
Image.__file__ = '/'

if hasattr(sys, 'frozen'):
    basedir = sys._MEIPASS
else:
    basedir = os.path.dirname(__file__)

im = Image.open(os.path.join(basedir, "tinysample.tiff"))
im.save(os.path.join(basedir, "tinysample.png"))
