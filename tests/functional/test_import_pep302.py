# -*- coding: utf-8 -*-
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

# PEP-302 import hooks specification contain section 'Optional Extensions to the Importer Protocol'
#
# This section is meant to be optional but the reality is different. Some Python modules (e.g. Flask) depends on
# implementation of these optional functions:
#
#   loader.is_package(fullmodname)
#   loader.get_code(fullmodname)
#   loader.get_source(fullmodname)
#
# This test-cases test the return values of these functions for importers from pyimod03_importers module.

# Note: The modules need to be imported at the end of the resp. code. Otherwise the pkgutil-functions take a very
#       different branch (since the module is already in sys.modules) and what we want to test will not be tested.


def test_pep302_loader_builtin(pyi_builder):
    pyi_builder.test_source(
        """
        mod = 'sys'
        import pkgutil
        ldr = pkgutil.get_loader(mod)
        assert ldr
        assert ldr.is_package(mod) == False
        assert ldr.get_code(mod) is None
        assert ldr.get_source(mod) is None
        """
    )


def test_pep302_loader_frozen_module(pyi_builder):
    pyi_builder.test_source(
        """
        mod = 'compileall'
        import pkgutil
        ldr = pkgutil.get_loader(mod)
        assert ldr
        assert ldr.is_package(mod) == False
        assert ldr.get_code(mod) is not None
        assert ldr.get_source(mod) is None
        # Import at the very end, just to get the module frozen.
        import compileall
        """
    )


def test_pep302_loader_frozen_package(pyi_builder):
    pyi_builder.test_source(
        """
        mod = 'distutils'
        import pkgutil
        ldr = pkgutil.get_loader(mod)
        assert ldr
        assert ldr.is_package(mod) == True
        assert ldr.get_code(mod) is not None
        assert ldr.get_source(mod) is None
        # Import at the very end, just to get the module frozen.
        import distutils
        """
    )


def test_pep302_loader_frozen_submodule(pyi_builder):
    pyi_builder.test_source(
        """
        mod = 'distutils.config'
        import pkgutil
        ldr = pkgutil.get_loader(mod)
        assert ldr
        assert ldr.is_package(mod) == False
        assert ldr.get_code(mod) is not None
        assert ldr.get_source(mod) is None
        # Import at the very end, just to get the module frozen.
        import distutils.config
        """
    )


def test_pep302_loader_cextension(pyi_builder):
    pyi_builder.test_source(
        """
        mod = '_sqlite3'
        import pkgutil
        ldr = pkgutil.get_loader(mod)
        assert ldr
        assert ldr.is_package(mod) == False
        assert ldr.get_code(mod) is None
        assert ldr.get_source(mod) is None
        # Import at the very end, just to get the module frozen.
        import sqlite3
        """
    )
