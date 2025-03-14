#-----------------------------------------------------------------------------
# Copyright (c) 2025, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import filecmp
import time

from PyInstaller.compat import is_win


def test_reproducible_subsequent_builds(pyi_builder, tmp_path, monkeypatch):
    from PyInstaller.archive.readers import CArchiveReader

    # On Windows, we need to set SOURCE_DATE_EPOCH for the build to be fully reproducible (i.e., the build timestamp
    # that is embedded in the executable)
    if is_win:
        monkeypatch.setenv('SOURCE_DATE_EPOCH', f"{time.time():.0f}")

    # Two consecutive builds; ensure their build and dist dirs are different
    pyi_builder._dist_dir = tmp_path / 'dist-1'
    pyi_builder._build_dir = tmp_path / 'build-1'
    pyi_builder.test_script('pyi_helloworld.py')
    executable1 = pyi_builder._find_executables("pyi_helloworld")[0]
    print("First executable:", executable1)

    pyi_builder._dist_dir = tmp_path / 'dist-2'
    pyi_builder._build_dir = tmp_path / 'build-2'
    pyi_builder.test_script('pyi_helloworld.py')
    executable2 = pyi_builder._find_executables("pyi_helloworld")[0]
    print("Second executable:", executable2)

    pkg1 = CArchiveReader(executable1)
    pkg2 = CArchiveReader(executable2)

    # First, compare TOCs of embedded PYZ archives - so we can get detailed error if their elements differ.
    def _find_pyz(pkg):
        pyz = [name for name, (*_, typecode) in pkg.toc.items() if typecode == 'z']
        return pyz[0]

    pyz1_name = _find_pyz(pkg1)
    pyz1 = pkg1.open_embedded_archive(pyz1_name)

    pyz2_name = _find_pyz(pkg2)
    pyz2 = pkg2.open_embedded_archive(pyz2_name)

    assert pyz1.toc == pyz2.toc

    # Compare PYZ archives bit-by-bit
    pyz1_data = pkg1.extract(pyz1_name)
    pyz2_data = pkg2.extract(pyz2_name)

    assert pyz1_data == pyz2_data

    # Compare PKG TOCs
    assert pkg1.toc == pkg2.toc
    assert pkg1.options == pkg2.options

    # Compare PKG archives bit-by-bit
    pkg1_data = pkg1.raw_pkg_data()
    pkg2_data = pkg2.raw_pkg_data()

    assert pkg1_data == pkg2_data

    # Compare whole executables
    assert filecmp.cmp(executable1, executable2, shallow=False)
