#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for PyGObject https://wiki.gnome.org/PyGObject
"""

from PyInstaller.utils.hooks import get_gi_typelibs

binaries, datas, hiddenimports = get_gi_typelibs('Gtk', '3.0')

import logging
logging = logging.getLogger(__name__)
logging.warn("GTK support is currently incomplete, please copy "
             "icons/fontconfig/locale/themes to your dist directory for "
             "your app to work correctly.")
