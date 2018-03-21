#-----------------------------------------------------------------------------
# Copyright (c) 2015-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This module, when imported as 'pyi_testmod_metapath1.extern.ccc.ddd', has
# actually has this __name__, even if the parent module's __name__ is
# 'pyi_testmod_metapath1._vendor.ccc'. This is since the parent module is
# known to sys.modules as '.extern.ccc'.

assert __name__.endswith('.ccc.ddd'), __name__
