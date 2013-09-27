#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# TODO check the purpose of this test case?

print("test_f_option - test 'f' option (just show os.environ)")

import os, sys

if sys.platform[:3] == 'win':
    print(" sorry, no use / need for the 'f' option on Windows")
else:
    print(' LD_LIBRARY_PATH %s' % os.environ.get('LD_LIBRARY_PATH', '<None!>'))

print('test_f_option complete')
