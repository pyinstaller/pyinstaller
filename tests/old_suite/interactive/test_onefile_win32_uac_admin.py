#-----------------------------------------------------------------------------
# Copyright (c) 2014-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
This test tests on Windows the option --uac-admin with onefile mode.

1) Upon execution the exe should ask for admin privileges.
2) Only admin user has access to path C:\Windows\Temp and this test
   should not fail when accessing this path.

"""


# Accessing directory where only admin has access.
import os
admin_dir = os.path.join(os.environ.get('SystemRoot','C:\\windows'), 'temp')
os.listdir(admin_dir)
