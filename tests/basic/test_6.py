#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys, os
import data6


print('data6.x is %s' % data6.x)

txt = """\
x = %d
""" % (data6.x + 1)


if hasattr(sys, 'frozen'):
    data6_filename = os.path.join(sys._MEIPASS, 'data6.py')
else:
    data6_filename = data6.__file__


open(data6_filename, 'w').write(txt)


reload(data6)
print('data6.x is now %s' % data6.x)
