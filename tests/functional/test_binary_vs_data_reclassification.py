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
#
# Basic tests for automatic binary vs. data file reclassification during anbalysis.

import pytest

import PyInstaller.utils.misc as miscutils
from PyInstaller.utils.tests import onedir_only


# Helpers
def _create_test_data_file(filename):
    filename.parent.mkdir(parents=True, exist_ok=True)
    # Create a text file
    filename.write_text("Test file", encoding='utf-8')


def _create_test_binary(filename):
    filename.parent.mkdir(parents=True, exist_ok=True)
    # Copy _ctypes extension
    import _ctypes
    import shutil
    shutil.copy2(_ctypes.__file__, filename)


def _create_test_build(pyi_builder, tmp_path, datas=None, binaries=None):
    extra_args = []
    for src_name, dest_name in datas or []:
        extra_args += ['--add-data', f"{src_name}:{dest_name}"]
    for src_name, dest_name in binaries or []:
        extra_args += ['--add-binary', f"{src_name}:{dest_name}"]

    pyi_builder.test_source("""
        print("Hello world!")
        """, pyi_args=extra_args)

    # Return path to the generated Analysis-XX.toc in the build directory
    analysis_toc_file = list((tmp_path / 'build' / 'test_source').glob("Analysis-*.toc"))
    assert len(analysis_toc_file) == 1
    analysis_toc_file = analysis_toc_file[0]

    # Load the serialized Analysis state, and take out the `binaries` and `datas` TOC lists.
    # The indices correspond to the lists' location in the `Analysis._guts`.
    analysis_data = miscutils.load_py_data_struct(analysis_toc_file)
    return (
        analysis_data[15],  # binaries
        analysis_data[18],  # datas
    )


# Test that we automatically reclassify a data file that was passed as a binary into its actual type.
@pytest.mark.linux
@pytest.mark.win32
@pytest.mark.darwin
@onedir_only
def test_automatic_reclassification_data_file(pyi_builder, tmp_path):
    binaries = []

    # Create test data file...
    src_path = tmp_path / 'test_file'
    _create_test_data_file(src_path)
    # ... and intentionally try to pass it as a binary.
    binaries.append((str(src_path), '.'))

    # Create test build and retrieve binaries and datas TOC lists
    binaries_toc, datas_toc = _create_test_build(pyi_builder, tmp_path, binaries=binaries)

    # We expect to find the test file's entry in the `datas` TOC list, and its typecode should be DATA.
    test_file_entries = [typecode for dest_name, src_name, typecode in binaries_toc if dest_name == 'test_file']
    assert len(test_file_entries) == 0

    test_file_entries = [typecode for dest_name, src_name, typecode in datas_toc if dest_name == 'test_file']
    assert len(test_file_entries) == 1
    assert test_file_entries[0] == 'DATA'


# Test that we automatically reclassify a binary that was passed as a data file into its actual type.
@pytest.mark.linux
@pytest.mark.win32
@pytest.mark.darwin
@onedir_only
def test_automatic_reclassification_binary(pyi_builder, tmp_path):
    datas = []

    # Create test binary...
    src_path = tmp_path / 'test_file'
    _create_test_binary(src_path)
    # ... and intentionally try to pass it as a data file.
    datas.append((str(src_path), '.'))

    # Create test build and retrieve binaries and datas TOC lists
    binaries_toc, datas_toc = _create_test_build(pyi_builder, tmp_path, datas=datas)

    # We expect to find the test file's entry in the `binaries` TOC list, and its typecode should be BINARY.
    test_file_entries = [typecode for dest_name, src_name, typecode in datas_toc if dest_name == 'test_file']
    assert len(test_file_entries) == 0

    test_file_entries = [typecode for dest_name, src_name, typecode in binaries_toc if dest_name == 'test_file']
    assert len(test_file_entries) == 1
    assert test_file_entries[0] == 'BINARY'
