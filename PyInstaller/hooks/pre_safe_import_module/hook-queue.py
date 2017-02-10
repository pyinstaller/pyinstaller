#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
warning for 'import queue' in 2.7 from the future

Problem appears to be that pyinstaller cannot have two modules of the same
name that differ only by lower/upper case.  The from the future 'queue' simply
imports all of the 'Queue' module.  So here we alias the 'queue' module to the
'Queue' module.
"""

from PyInstaller.compat import is_py2
from PyInstaller.utils.hooks import logger

def pre_safe_import_module(api):
    if is_py2:
        logger.warning("import queue, not supported, will use Queue")
        api.add_alias_module('Queue', 'queue')
