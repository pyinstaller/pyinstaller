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

import os
import pathlib

import pytest

import PyInstaller.utils.misc as miscutils


# Helpers
def _create_test_data_file(filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # Create a text file
    with open(filename, 'w', encoding='utf-8') as fp:
        fp.write("Test file")


def _create_test_binary(filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    # Copy _ctypes extension
    import _ctypes
    import shutil
    shutil.copy2(_ctypes.__file__, filename)


def _create_test_build(pyi_builder, tmpdir, datas=None, binaries=None):
    extra_args = []
    for src_name, dest_name in datas or []:
        extra_args += ['--add-data', f"{src_name}{os.pathsep}{dest_name}"]
    for src_name, dest_name in binaries or []:
        extra_args += ['--add-binary', f"{src_name}{os.pathsep}{dest_name}"]

    pyi_builder.test_source("""
        print("Hello world!")
        """, pyi_args=extra_args)

    # Return path to the generated Analysis-XX.toc in the build directory
    analysis_toc_file = list((pathlib.Path(tmpdir) / "build/test_source").glob("Analysis-*.toc"))
    assert len(analysis_toc_file) == 1
    analysis_toc_file = analysis_toc_file[0]

    # Load the serialized Analysis state, and take out the `binaries` and `datas` TOC lists.
    # The indices correspond to the lists' location in the `Analysis._guts`.
    analysis_data = miscutils.load_py_data_struct(analysis_toc_file)
    return (
        analysis_data[14],  # binaries
        analysis_data[17],  # datas
    )


# Test that we automatically reclassify a data file that was passed as a binary into its actual type.
@pytest.mark.linux
@pytest.mark.win32
@pytest.mark.darwin
@pytest.mark.parametrize('pyi_builder', ['onedir'], indirect=True)  # Run only in onedir mode.
def test_automatic_reclassification_data_file(pyi_builder, tmpdir):
    binaries = []

    # Create test data file...
    src_path = os.path.join(tmpdir, 'test_file')
    _create_test_data_file(src_path)
    # ... and intentionally try to pass it as a binary.
    binaries.append((src_path, '.'))

    # Create test build and retrieve binaries and datas TOC lists
    binaries_toc, datas_toc = _create_test_build(pyi_builder, tmpdir, binaries=binaries)

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
@pytest.mark.parametrize('pyi_builder', ['onedir'], indirect=True)  # Run only in onedir mode.
def test_automatic_reclassification_binary(pyi_builder, tmpdir):
    datas = []

    # Create test binary...
    src_path = os.path.join(tmpdir, 'test_file')
    _create_test_binary(src_path)
    # ... and intentionally try to pass it as a data file.
    datas.append((src_path, '.'))

    # Create test build and retrieve binaries and datas TOC lists
    binaries_toc, datas_toc = _create_test_build(pyi_builder, tmpdir, datas=datas)

    # We expect to find the test file's entry in the `binaries` TOC list, and its typecode should be BINARY.
    test_file_entries = [typecode for dest_name, src_name, typecode in datas_toc if dest_name == 'test_file']
    assert len(test_file_entries) == 0

    test_file_entries = [typecode for dest_name, src_name, typecode in binaries_toc if dest_name == 'test_file']
    assert len(test_file_entries) == 1
    assert test_file_entries[0] == 'BINARY'
