#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import get_pyextension_imports


# It's hard to detect imports of binary Python module without importing it.
# Let's try importing that module in a subprocess.
# TODO function get_pyextension_imports() is experimental and we need
#      to evaluate its usage here and its suitability for other hooks.
hiddenimports = get_pyextension_imports('pyodbc')
