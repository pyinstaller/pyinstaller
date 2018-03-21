#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# distutils module requires Makefile and pyconfig.h files from Python
# installation.


import os
import sys
import sysconfig


config_h = sysconfig.get_config_h_filename()
print(('pyconfig.h: ' + config_h))
files = [config_h]


# On Windows Makefile does not exist.
if not sys.platform.startswith('win'):
    makefile = sysconfig.get_makefile_filename()
    print(('Makefile: ' + makefile))
    files.append(makefile)


for f in files:
    if not os.path.exists(f):
        raise SystemExit('File does not exist: %s' % f)
