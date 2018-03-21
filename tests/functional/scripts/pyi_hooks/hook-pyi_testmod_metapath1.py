#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules

# pyi_testmod_metapath1._vendor is not imported directly and won't be
# found by modulegraph. So, explicitly include this sub-package.
hiddenimports = collect_submodules('pyi_testmod_metapath1._vendor')
