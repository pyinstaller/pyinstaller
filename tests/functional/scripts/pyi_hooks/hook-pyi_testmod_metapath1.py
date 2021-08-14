#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules

# pyi_testmod_metapath1._vendor is not imported directly and will not be found by modulegraph.
# So, explicitly include this sub-package.
hiddenimports = collect_submodules('pyi_testmod_metapath1._vendor')
