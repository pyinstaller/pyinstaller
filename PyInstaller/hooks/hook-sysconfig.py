#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import sysconfig

from PyInstaller.compat import is_win


if not is_win and hasattr(sysconfig, '_get_sysconfigdata_name'):
    # Python 3.6 uses additional modules like
    # `_sysconfigdata_m_linux_x86_64-linux-gnu`, see
    # https://github.com/python/cpython/blob/3.6/Lib/sysconfig.py#L417
    # Note: Some versions of Anaconda backport this feature to before 3.6.
    # See issue #3105
    hiddenimports = [sysconfig._get_sysconfigdata_name()]
