#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for Gio https://developer.gnome.org/gio/stable/ from the GLib library https://wiki.gnome.org/Projects/GLib
introspected through PyGobject https://wiki.gnome.org/PyGObject via the GObject Introspection middleware layer
https://wiki.gnome.org/Projects/GObjectIntrospection

Tested with GLib 2.44.1, PyGObject 3.16.2, GObject Introspection 1.44.0 on Mac OS X 10.10.5 and
GLib 2.42.2, PyGObject 3.14.0, and GObject Introspection 1.42 on Windows 7
"""

import glob
import os
import sys

import PyInstaller.log as logging
from PyInstaller.compat import is_darwin, is_win
from PyInstaller.utils.hooks import get_typelibs, exec_statement

logger = logging.getLogger(__name__)


hiddenimports = ['gi.overrides.Gio']


datas = get_typelibs('Gio', '2.0')


binaries = []

statement = """
from gi.repository import Gio
print(Gio.__path__)
"""

path = exec_statement(statement)
pattern = None

if is_darwin:
    # Use commonprefix to find common prefix between sys.prefix and the path, e.g.,
    # /opt/local/Library/Frameworks/Python.framework/Versions/3.4,
    # and /opt/local/lib/girepository-1.0/Gio-2.0.typelib.
    # Then use that and the standard Gio modules path of <prefix>/lib/gio/modules/ to gather the modules.
    pattern = os.path.join(os.path.commonprefix([sys.prefix, path]), 'lib', 'gio', 'modules', '*.so')
elif is_win:
    # Don't use common prefix since sys.prefix on Windows in usually C:\Python<version> and Gio's modules
    # are installed at C:\Python<version>\Lib\site-packages\gnome\lib\gio\modules which wouldn't yield a useful prefix.
    # By just backing up a directory level from the Gio typelib we are then in the gnome lib directory and can then
    # use the standard Gio modules path to gather the modules.
    pattern = os.path.join(os.path.dirname(path), '..', 'gio', 'modules', '*.dll')

if pattern:
    for f in glob.glob(pattern):
        binaries.append((f, 'gio_modules'))
else:
    # To add a new platform add a new elif above with the proper is_<platform> and
    # proper pattern for finding the Gio modules on your platform.
    logger.warn('Bundling Gio modules is currently not supported on your platform.')
