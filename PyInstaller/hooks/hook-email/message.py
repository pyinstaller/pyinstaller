#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
email.message imports the old-style naming of two modules:
email.Iterators and email.Generator. Since those modules
don't exist anymore and there are import trick to map them
to the real modules (lowercase), we need to specify them
as hidden imports to make PyInstaller package them.
"""


hiddenimports = [ "email.iterators", "email.generator" ]
