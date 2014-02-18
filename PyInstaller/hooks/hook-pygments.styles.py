#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
# Because this is pygments.styles, note the .. required in order to get back to the hooks subdirectory.
from ..hookutils import collect_submodules

# Pygments uses a dynamic import for its formatters, so gather them all here.
hiddenimports = collect_submodules('pygments.styles')
