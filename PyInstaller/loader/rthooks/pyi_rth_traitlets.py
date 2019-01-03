#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# 'traitlets' uses module 'inspect' from default Python library to inspect
# source code of modules. However, frozen app does not contain source code
# of Python modules.
#
# hook-IPython depends on module 'traitlets'.

import traitlets.traitlets

def _disabled_deprecation_warnings(method, cls, method_name, msg):
    pass

traitlets.traitlets._deprecated_method = _disabled_deprecation_warnings