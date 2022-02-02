#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules, is_module_satisfies, collect_data_files

# pkg_resources keeps vendored modules in its _vendor subpackage, and does sys.meta_path based import magic to expose
# them as pkg_resources.extern.*
hiddenimports = collect_submodules('pkg_resources._vendor')

# pkg_resources v45.0 dropped support for Python 2 and added this module printing a warning. We could save some bytes if
# we would replace this by a fake module.
hiddenimports.append('pkg_resources.py2_warn')

excludedimports = ['__main__']

# Some more hidden imports. See:
# https://github.com/pyinstaller/pyinstaller-hooks-contrib/issues/15#issuecomment-663699288 `packaging` can either be
# its own package, or embedded in `pkg_resources._vendor.packaging`, or both. Assume the worst and include both if
# present.
hiddenimports += collect_submodules('packaging')

hiddenimports += ['pkg_resources.markers']

# As of v60.7, setuptools vendored jaraco and has pkg_resources use it. There is a custom importer,
# pkg_resources.extern.VendorImporter, that is used to find the vendored package, and redirects
# pkg_resources.extern.jaraco to pkg_resources._vendor.jaraco. Unfortunately, that does not seem to play nicely with
# our FrozenImporter, so for now, we work around that by collecting all pkg_resources._vendor.jaraco submodules as
# source .py files and let the VendorImporter deal with them (which also means we need to ensure that we do not collect
# any of those modules into our PYZ archive).
if is_module_satisfies("setuptools >= 60.7"):
    excludedimpoirts = ["pkg_resources._vendor.jaraco"]
    # Despite its appearance, this actually collects all source files from pkg_resources._vendor.jaraco (plus the
    # "Lorem Ipsum.txt" data file from pkg_resources._vendor.jaraco.text if it is present). Calling collect_data_files
    # on pkg_resources._vendor.jaraco itself does not work due to bug(s) in its handling of namespace packages.
    datas = collect_data_files(
        'pkg_resources._vendor.jaraco.functools', include_py_files=True, excludes=['**/__pycache__']
    )
