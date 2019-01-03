#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
codegen generates Python code that is then executed through exec().
This Python code imports the following modules.
"""


hiddenimports = ['mako.cache', 'mako.runtime', 'mako.filters']
