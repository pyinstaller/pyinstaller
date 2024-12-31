#-----------------------------------------------------------------------------
# Copyright (c) 2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


# A basic lazy loader test with a stdlib module
def test_importlib_lazy_loader(pyi_builder):
    pyi_builder.test_script(
        'pyi_lazy_import.py',
        app_args=['json'],
        pyi_args=['--hiddenimport', 'json'],
    )


# NOTE: the tests with aliased module used to be based on `pkg_resources._vendor.jaraco.text` and
# `pkg_resources.extern.jaraco.text`. However, `pkg_resources` shipped with `setuptools` >= 71  does not vendor its
# dependencies anymore, so those modules are gone. Therefore, the tests are now using `pyi_testmod_metapath1` from
# `test_import_metapath1`, which implements a copy of `VendorImporter` used by earlier versions of `setuptools`.


# Lazy loader test with aliased module - using original name
def test_importlib_lazy_loader_alias1(pyi_builder, script_dir):
    pyi_builder.test_script(
        'pyi_lazy_import.py',
        app_args=['pyi_testmod_metapath1._vendor.ccc.ddd'],
        pyi_args=[
            '--hiddenimport',
            'pyi_testmod_metapath1',
            '--additional-hooks-dir',
            str(script_dir / 'pyi_hooks'),
        ],
    )


# Lazy loader test with aliased module - using alias
def test_importlib_lazy_loader_alias2(pyi_builder, script_dir):
    pyi_builder.test_script(
        'pyi_lazy_import.py',
        app_args=['pyi_testmod_metapath1.extern.ccc.ddd'],
        pyi_args=[
            '--hiddenimport',
            'pyi_testmod_metapath1',
            '--additional-hooks-dir',
            str(script_dir / 'pyi_hooks'),
        ],
    )
