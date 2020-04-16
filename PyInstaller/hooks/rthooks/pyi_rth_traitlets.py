#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
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