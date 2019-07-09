#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Hook for https://pypi.python.org/pypi/jira/
"""

from PyInstaller.utils.hooks import copy_metadata, collect_submodules

datas = copy_metadata('jira')
hiddenimports = collect_submodules('jira')
