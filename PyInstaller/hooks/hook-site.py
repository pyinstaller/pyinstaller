#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# In virtualenv, site.py module is overriden. We need to bundle the real
# site.py module.

import os
import sys

from PyInstaller.compat import is_virtualenv, is_win


def hook(mod):
    if is_virtualenv:
        # Workaround to get real path of site.py module.
        if is_win:
            mod_path = os.path.join(sys.real_prefix, 'Lib', 'site.py')
        else:
            mod_path = os.path.join(sys.real_prefix, 'lib',
                                    'python'+sys.version[:3], 'site.py')
            mod64_path = os.path.join(sys.real_prefix, 'lib64',
                                      'python'+sys.version[:3], 'site.py')
            if os.path.exists(mod64_path):
                mod_path = mod64_path
        mod.retarget(mod_path)
    return mod
