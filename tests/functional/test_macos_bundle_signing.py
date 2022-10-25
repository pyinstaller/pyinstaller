#-----------------------------------------------------------------------------
# Copyright (c) 2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
#
# Basic tests for macOS app bundle data relocation and code signing.

import pytest

from PyInstaller.utils.tests import importorskip


# Test that collected metadata is properly relocated to avoid codesign errors due to directory containing dots in name.
@pytest.mark.darwin
@importorskip('psutil')
@pytest.mark.parametrize('pyi_builder', ['onedir'], indirect=True)  # Run only in onedir mode.
def test_macos_bundle_signing_metadata(pyi_builder, monkeypatch):
    # Have codesign errors terminate the build instead of generating a warning.
    monkeypatch.setenv("PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR", "1")

    pyi_builder.test_source("""
        import psutil
        """, pyi_args=['--windowed', '--copy-metadata', 'psutil'])


# Test that the bundle signing works even if we collect a package as source .py files, which we do not relocate.
@pytest.mark.darwin
@importorskip('psutil')
@pytest.mark.parametrize('pyi_builder', ['onedir'], indirect=True)  # Run only in onedir mode.
def test_macos_bundle_signing_py_files(pyi_builder, monkeypatch):
    # Have codesign errors terminate the build instead of generating a warning.
    monkeypatch.setenv("PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR", "1")

    # Override Analysis so that we can set package collection mode without having to use .spec file.
    def AnalysisOverride(*args, **kwargs):
        kwargs['module_collection_mode'] = {'psutil': 'py'}
        return Analysis(*args, **kwargs)

    import PyInstaller.building.build_main
    Analysis = PyInstaller.building.build_main.Analysis
    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', AnalysisOverride)

    pyi_builder.test_source("""
        import psutil
        """, pyi_args=['--windowed'])


# Test that the codesigning works even if we collect a package as .pyc files, which we do not relocate.
@pytest.mark.darwin
@importorskip('psutil')
@pytest.mark.parametrize('pyi_builder', ['onedir'], indirect=True)  # Run only in onedir mode.
def test_macos_bundle_signing_pyc_files(pyi_builder, monkeypatch):
    # Have codesign errors terminate the build instead of generating a warning.
    monkeypatch.setenv("PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR", "1")

    # Override Analysis so that we can set package collection mode without having to use .spec file.
    def AnalysisOverride(*args, **kwargs):
        kwargs['module_collection_mode'] = {'psutil': 'pyc'}
        return Analysis(*args, **kwargs)

    import PyInstaller.building.build_main
    Analysis = PyInstaller.building.build_main.Analysis
    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', AnalysisOverride)

    pyi_builder.test_source("""
        import psutil
        """, pyi_args=['--windowed'])
