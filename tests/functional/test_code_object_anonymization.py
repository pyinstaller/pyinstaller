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

import collections
import os
import io
import marshal
import zipfile

from PyInstaller.loader.pyimod01_archive import PYZ_ITEM_MODULE, PYZ_ITEM_PKG
from PyInstaller.archive.readers import CArchiveReader, PKG_ITEM_PYPACKAGE, PKG_ITEM_PYMODULE, PKG_ITEM_PYSOURCE


def _analyze_collected_code_objects(filename):
    # Construct lists of expected and found co_filename values, along with metadata (pkg/pyz and name). We compare these
    # lists at the end, and rely on pytest to produce a nicely formatted diff if there is a mismatch....
    Entry = collections.namedtuple('Entry', ['location', 'name', 'co_filename'])
    expected_entries = []
    found_entries = []

    # PKG archive: all modules and scripts - bootstrap modules, bootstrap script, run-time hooks, entry-point script.
    pkg_archive = CArchiveReader(filename)

    for name, (*_, typecode) in pkg_archive.toc.items():
        if typecode not in {PKG_ITEM_PYPACKAGE, PKG_ITEM_PYMODULE, PKG_ITEM_PYSOURCE}:
            continue

        expected_co_filename = name + '.py'
        expected_entries.append(Entry('PKG', name, expected_co_filename))

        code_object = marshal.loads(pkg_archive.extract(name))
        found_entries.append(Entry('PKG', name, code_object.co_filename))

    # base_library.zip - either in PKG archive, or in _internal next to executable.
    baselib_zip_filename = os.path.join(os.path.dirname(filename), '_internal', 'base_library.zip')
    if os.path.isfile(baselib_zip_filename):
        baselib_zip = zipfile.ZipFile(baselib_zip_filename, mode='r')
    else:
        # onefile mode
        baselib_zip = zipfile.ZipFile(io.BytesIO(pkg_archive.extract('base_library.zip')), mode='r')

    for entry in baselib_zip.infolist():
        # Turn the entry filename into expected co_filename by changing .pyc extension into .py. The entries in .zip
        # file have POSIX separators, which need to be normalized for comparison on Windows.
        expected_co_filename = os.path.normpath(entry.filename)[:-1]
        expected_entries.append(Entry('base_library.zip', entry.filename, expected_co_filename))

        code_object = marshal.loads(baselib_zip.read(entry)[16:])  # skip the .pyc header (16 bytes)
        found_entries.append(Entry('base_library.zip', entry.filename, code_object.co_filename))

    # PYZ archive: all modules and packages.
    pyz_archive = pkg_archive.open_embedded_archive('PYZ.pyz')

    for name, (typecode, *_) in pyz_archive.toc.items():
        # Analyze only modules and packages (i.e., ignore PEP-420 namespace package entries).
        if typecode not in {PYZ_ITEM_MODULE, PYZ_ITEM_PKG}:
            continue

        if typecode == PYZ_ITEM_MODULE:
            expected_co_filename = os.path.join(*name.split('.')) + '.py'
        else:
            expected_co_filename = os.path.join(*name.split('.'), '__init__.py')
        expected_entries.append(Entry('PYZ', name, expected_co_filename))

        code_object = pyz_archive.extract(name)
        found_entries.append(Entry('PYZ', name, code_object.co_filename))

    # Compare the obtained lists
    assert expected_entries == found_entries


def test_co_filename_anonymization(pyi_builder):
    pyi_args = [
        # stdlib packages with run-time hooks
        '--hiddenimport',
        'inspect',
        '--hiddenimport',
        'multiprocessing',
        # setuptools for its vendored packages
        '--hiddenimport',
        'setuptools',
        # PyInstaller's "fake" modules/packages
        '--hiddenimport',
        'pyi_splash',
        '--hiddenimport',
        '_pyi_rth_utils.tempfile',
        '--hiddenimport',
        '_pyi_rth_utils.qt',
    ]

    pyi_builder.test_source("""
        print("Hello!")
        """, pyi_args=pyi_args)

    executables = pyi_builder._find_executables("test_source")
    assert len(executables) == 1

    _analyze_collected_code_objects(executables[0])
