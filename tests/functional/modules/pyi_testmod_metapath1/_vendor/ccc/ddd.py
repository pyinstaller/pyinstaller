#-----------------------------------------------------------------------------
# Copyright (c) 2015-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# This module, when imported as 'pyi_testmod_metapath1.extern.ccc.ddd', has actually has this __name__, even if the
# parent module's __name__ is 'pyi_testmod_metapath1._vendor.ccc'. This is because the parent module is known to
# sys.modules as '.extern.ccc'.

assert __name__.endswith('.ccc.ddd'), __name__
