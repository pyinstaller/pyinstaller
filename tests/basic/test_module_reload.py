#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# PyInstaller always loads modules from the embedded archive before
# looking at sys.path.
#
# This tests creates module with the same name as the one in the
# embbedded archive. Python should always load module from the
# embedded archive.


import sys, os
import data_reload


orig_x = data_reload.x
print('data_reload.x is %s' % data_reload.x)

txt = """\
x = %d
""" % (data_reload.x + 1)


if hasattr(sys, 'frozen'):
    module_filename = os.path.join(sys._MEIPASS, 'data_reload.py')
else:
    module_filename = data_reload.__file__


open(module_filename, 'w').write(txt)


reload(data_reload)
print('data_reload.x is now %s' % data_reload.x)


# The value of 'x' should be the same as before reloading the module.
assert orig_x == data_reload.x
