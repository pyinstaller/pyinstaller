#-----------------------------------------------------------------------------
# Copyright (c) 2017-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


# Hook for the unidecode package: https://pypi.python.org/pypi/unidecode
# Tested with Unidecode 0.4.21 and Python 3.6.2, on Windows 10 x64.

from PyInstaller.utils.hooks import collect_submodules

# Unidecode dynamically imports modules with relevant character mappings.
# Non-ASCII characters are ignored if the mapping files are not found.
hiddenimports = collect_submodules('unidecode')
