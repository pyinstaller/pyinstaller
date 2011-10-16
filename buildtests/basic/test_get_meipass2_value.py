# Bootloader unsets _MEIPASS2 for child processes so that if the program
# invokes another PyInstaller one-file program as subprocess, this
# subprocess will not fooled into thinking that it is already unpacked.
#
# This test checks if it is really unset.

import os
import sys
import subprocess

#print '_____MEIPASS2', os.environ['_MEIPASS2']


if sys.platform.startswith('win'):
    command = 'echo %_MEIPASS2%'
else:
    command = 'echo $_MEIPASS2'


proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
proc.wait()
stdout, stderr = proc.communicate()

meipass = stdout.strip()

# win32 fix
if meipass.startswith(r'%'):
    meipass = ''

print meipass
print '_MEIPASS2 value:', sys._MEIPASS

if meipass:
    raise SystemExit('Error: _MEIPASS2 env variable available in subprocess.')
