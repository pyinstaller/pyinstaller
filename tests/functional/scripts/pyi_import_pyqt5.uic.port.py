#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This requires you hand-crafted PyQt5 package, since some
# distributions do not include PyQt5.uic.port_v3 for Python and the
# other way round.
#
# PyQt5.uic.port_v3.test raises an AssertionError if imported under
# Python 3. But the hook should prohibit the inclusion of this module,
# so an ImportError should be raised. So the ImportError is what we
# expect and we just ignore it.


import PyQt5

# Ensure it's our fake module
assert PyQt5.__pyinstaller_fake_module_marker__ == '__pyinstaller_fake_module_marker__'

try:
    import PyQt5.uic.port_v3
    print(PyQt5.uic.port_v3.__path__)
except ImportError:
    print('PyQt5.uic.port_v3 not imported')
    pass

# This is the same, just for Python3 importing PyQT5.uic.port_v2.test
try:
    import PyQt5.uic.port_v2
    print(PyQt5.uic.port_v2.__path__)
except ImportError:
    print('PyQt5.uic.port_v2 not imported')
    pass
