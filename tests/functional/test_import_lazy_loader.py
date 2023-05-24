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

from PyInstaller.utils.tests import importorskip


# A basic lazy loader test with a stdlib module
def test_importlib_lazy_loader(pyi_builder):
    pyi_builder.test_script(
        'pyi_lazy_import.py',
        app_args=['json'],
        pyi_args=['--hiddenimport', 'json'],
    )


# Lazy loader test with aliased module - using original name
@importorskip('pkg_resources._vendor.jaraco.text')
def test_importlib_lazy_loader_alias1(pyi_builder):
    pyi_builder.test_script(
        'pyi_lazy_import.py',
        app_args=['pkg_resources._vendor.jaraco.text'],
        pyi_args=['--hiddenimport', 'pkg_resources'],
    )


# Lazy loader test with aliased module - using alias
@importorskip('pkg_resources.extern.jaraco.text')
def test_importlib_lazy_loader_alias2(pyi_builder):
    pyi_builder.test_script(
        'pyi_lazy_import.py',
        app_args=['pkg_resources.extern.jaraco.text'],
        pyi_args=['--hiddenimport', 'pkg_resources'],
    )
