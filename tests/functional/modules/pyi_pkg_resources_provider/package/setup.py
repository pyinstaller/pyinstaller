#-----------------------------------------------------------------------------
# Copyright (c) 2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# This assists in creating an ``.egg`` package for use with the ``test_pkg_resources_provider``. To build the package,
# execute ``python setup.py bdist_egg``.

import setuptools

setuptools.setup(
    name='pyi_pkgres_testpkg',
    version='1.0.0',
    setup_requires="setuptools >= 40.0.0",
    author='PyInstaller development team',
    packages=setuptools.find_packages(),
    package_data={
        "pyi_pkgres_testpkg": [
            "subpkg1/data/*.txt",
            "subpkg1/data/*.md",
            "subpkg1/data/*.rst",
            "subpkg1/data/extra/*.json",
            "subpkg3/*.json",
        ],
    }
)
