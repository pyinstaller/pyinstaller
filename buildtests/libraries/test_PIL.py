import sys
import os

import PIL.Image

# disable "leaking" the installed version
PIL.Image.__file__ = '/'

if hasattr(sys, 'frozen'):
    basedir = sys._MEIPASS
else:
    basedir = os.path.dirname(__file__)

im = PIL.Image.open(os.path.join(basedir, "tinysample.tiff"))
im.save(os.path.join(basedir, "tinysample.png"))
