#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
from hookutils import collect_submodules

# Pygments uses a dynamic import for its formatters, lexers,
# and styles. There's a filter submodule, but nothing there
# so it's not included in this list.
hiddenimports = (
    collect_submodules('pygments.formatters') + 
    collect_submodules('pygments.lexers') + 
    collect_submodules('pygments.styles'))
