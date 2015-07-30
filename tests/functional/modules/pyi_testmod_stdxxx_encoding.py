#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import sys
import subprocess

# For various OSes the encoding is different.
if sys.platform.startswith('win'):
    if sys.version_info[0] == 2:
        # The default Windows encoding is based on the active console code page,
        # which varies from PC to PC and may be changed by the user. For more info,
        # See https://technet.microsoft.com/en-us/library/bb490874.aspx.
        # Therefore, ask for the current encoding using chcp (see link above
        # for details). The expected output: 'Active code page: nnn\r\n'.
        # We want only the nnn (a number which specifies the code page).
        chcp_out = subprocess.check_output(['chcp'])
        # The encoding consists of the string `cpnnn`, where the nnn is replaced
        # by the active code page.
        encoding = 'cp' + chcp_out.split()[-1]
    else:
        # For Python 3 the code page is different if it runs on the active console
        # or not.
        # In the interactive console MS-DOS code pages are used (cp852) otherwise
        # ansi code pages are used (e.g. cp1250).
        # The test suite runs this test in a non-interactive console.
        #
        # The app created by PyInstaller reports the same encoding as from
        # locale.getpreferredencoding()
        import locale
        encoding = locale.getpreferredencoding(False)
else:
    # On Linux, MAC OS X, and other Unixes it should be mostly 'UTF-8'.
    encoding = 'UTF-8'

