#-----------------------------------------------------------------------------
# Copyright (c) 2013-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
# This hook is applied to all packages that don't have a hook defined. It
# includes all files from the package.
from PyInstaller.utils.hooks import collect_all


# PyInstaller will call this function when processing the hook.
def hook(hook_api):
    # Insert the package this hook is being applied to. The name gives the
    # module inside the package; use this to find the package.
    package_name = hook_api.__name__.split('.', 1)[0]

    datas, binaries, hiddenimports = collect_all(package_name)
    hook_api.add_datas(datas)
    hook_api.add_binaries(binaries)
    hook_api.add_imports(*hiddenimports)
