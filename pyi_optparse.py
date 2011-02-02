"""
optparse -- forward-compatibility wrapper for use with Python 2.2.x and
earlier.  If you import from 'optparse' rather than 'optik', your code
will work on base Python 2.3 (and later), or on earlier Pythons with
Optik 1.4.1 or later installed.
"""

try:
    from optparse import __version__, __all__
    from optparse import *
except:
    from PyInstaller.lib.optik import __version__, __all__
    from PyInstaller.lib.optik import *
