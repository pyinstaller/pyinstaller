#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# This requires a custom hand-crafted PyQt5 package, since some distributions do not include PyQt5.uic.port_v3
# for Python 2 and the other way round.
#
# PyQt5.uic.port_v2.test raises an AssertionError if imported under Python 3. But the hook should prohibit the
# inclusion of this module, so an ImportError should be raised. Therefore, the ImportError is what we expect
# and we just ignore it.

import PyQt5

# Ensure PyQt5 is our fake package.
assert PyQt5.__pyinstaller_fake_module_marker__ == '__pyinstaller_fake_module_marker__'

import PyQt5.uic.port_v3  # noqa: E402

print(PyQt5.uic.port_v3.__path__)

try:
    import PyQt5.uic.port_v2
    print(PyQt5.uic.port_v2.__path__)
except ImportError:
    print('PyQt5.uic.port_v2 not imported')
    pass
