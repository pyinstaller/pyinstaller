#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Bootloader unsets _MEIPASS2 for child processes so that if the program
# invokes another PyInstaller one-file program as subprocess, this
# subprocess will not fooled into thinking that it is already unpacked.
#
# This test checks if it is really unset in a subprocess.


import os
import subprocess
import sys


def _get_meipass_value():
    if sys.platform.startswith('win'):
        command = 'echo %_MEIPASS2%'
    else:
        command = 'echo $_MEIPASS2'

    stdout = subprocess.check_output(command, shell=True)
    meipass = stdout.strip()

    # Win32 fix.
    if meipass.startswith(b'%'):
        meipass = ''


    return meipass


meipass = _get_meipass_value()



print(meipass)
print(('_MEIPASS2 value: %s' % sys._MEIPASS))


if meipass:
    raise SystemExit('Error: _MEIPASS2 env variable available in subprocess.')
