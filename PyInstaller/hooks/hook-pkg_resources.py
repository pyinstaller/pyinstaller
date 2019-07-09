#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_submodules

# pkg_resources keeps vendored modules in its _vendor subpackage, and does
# sys.meta_path based import magic to expose them as pkg_resources.extern.*
hiddenimports = collect_submodules('pkg_resources._vendor')
