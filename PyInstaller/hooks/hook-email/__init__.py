#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.compat import is_py2


# These modules must be included with 'email' module for
# lazy loading to provide name mapping from new-style (lower case) names
# email.<old name> -> email.<new name is lowercased old name>
# email.MIME<old name> -> email.mime.<new name is lowercased old name>
# The old module names are removed in Python 3.
if is_py2:
    import email
    hiddenimports = ['email.' + x.lower() for x in email._LOWERNAMES]
    hiddenimports += ['email.mime.' + x.lower() for x in email._MIMENAMES]
