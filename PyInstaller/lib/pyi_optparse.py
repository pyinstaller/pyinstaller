"""
optparse -- forward-compatibility wrapper for use with Python 2.2.x and
earlier.  If you import from 'optparse' rather than 'optik', your code
will work on base Python 2.3 (and later), or on earlier Pythons with
Optik 1.4.1 or later installed.
"""

# Please note: This module MUST NOT be renamed to optparse.py, since
# `from optparse import ...` would recursivly import this module.
# This is due the missing of absolut imports prior to Python 2.5

try:
    from optparse import __version__, __all__
    from optparse import *
except:
    from PyInstaller.lib.optik import __version__, __all__
    from PyInstaller.lib.optik import *
