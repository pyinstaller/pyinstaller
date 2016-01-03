#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Python library httplib does not work when trying to use ssl. The following
modules should be included with httplib.
"""


hiddenimports = ['_ssl', 'ssl']
