#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This import forces Python 2 to handle string as unicode - as with prefix 'u'.
from __future__ import unicode_literals

# Convert type 'bytes' to type 'str' (Py3) or 'unicode' (Py2).
assert b'foo'.decode('ascii') == 'foo'
