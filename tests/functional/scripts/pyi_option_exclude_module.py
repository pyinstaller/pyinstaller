#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


try:
    import xml.sax
    # Option --exclude-module=xml.sax did not work and the module was successfully
    # imported.
    raise SystemExit('Module xml.sax was excluded but it is bundled with the executable.')
except ImportError:
    # Import error is expected since PyInstaller should not bundle 'xml.sax' module.
    pass
