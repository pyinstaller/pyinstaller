#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
#
# *****************************************************
# hook-pygments.py - PyInstaller hook file for pygments
# *****************************************************
# The following applies to pygments version 2.0.2, as reported by ``pip show
# pygments``.
#
# From pygments.formatters, line 37::
#
#    def _load_formatters(module_name):
#        """Load a formatter (and all others in the module too)."""
#        mod = __import__(module_name, None, None, ['__all__'])
#
# Therefore, we need all the modules in ``pygments.formatters``.
from PyInstaller.hooks.hookutils import collect_submodules
hiddenimports = collect_submodules('pygments.formatters')

