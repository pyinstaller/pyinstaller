#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import subprocess


frozen_encoding = str(sys.stderr.encoding)

# For various OSes the encoding is different.
if sys.platform.startswith('win'):
    # The default Windows encoding is based on the active console code page,
    # which varies from PC to PC and may be changed by the user. For more info,
    # See https://technet.microsoft.com/en-us/library/bb490874.aspx.
    # Therefore, ask for the current encoding using chcp (see link above
    # for details). The expected output: 'Active code page: nnn\r\n'.
    # We want only the nnn (a number which specifies the code page).
    chcp_out = subprocess.check_output(['chcp'], shell=True)
    # The encoding consists of the string `cpnnn`, where the nnn is replaced
    # by the active code page.
    encoding = 'cp' + chcp_out.split()[-1]
else:
    # On Linux, MAC OS X, and other Unixes it should be mostly 'UTF-8'.
    encoding = 'UTF-8'

print('Encoding expected: ' + encoding)
print('Encoding current: ' + frozen_encoding)

if not frozen_encoding == encoding:
    raise SystemExit('Frozen encoding %s is not the same as unfrozen %s.' %
                     (frozen_encoding, encoding))

