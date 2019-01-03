#-----------------------------------------------------------------------------
# Copyright (c) 2015-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import is_module_satisfies
from PyInstaller import log as logging

if is_module_satisfies('kivy >= 1.9.1'):
    from kivy.tools.packaging.pyinstaller_hooks import (
        add_dep_paths, excludedimports, datas, get_deps_all,
        get_factory_modules, kivy_modules)

    add_dep_paths()

    hiddenimports = get_deps_all()['hiddenimports']
    hiddenimports = list(set(get_factory_modules() + kivy_modules +
                             hiddenimports))
else:
    logger = logging.getLogger(__name__)
    logger.warning('Hook disabled because of Kivy version < 1.9.1')
