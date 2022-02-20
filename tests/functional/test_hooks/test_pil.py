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
"""
Functional tests for the Python Imaging Library (PIL).

Note that the original unmaintained PIL has been obsoleted by the PIL-compatible fork Pillow,
which retains the same Python package `PIL`.
"""

import pytest

from PyInstaller.utils.tests import importorskip, skip
from PyInstaller.utils.hooks import can_import_module


# "excludedimports" support is currently non-deterministic and hence cannot be marked as @xfail. If this test was
# marked as @xfail but succeeded, py.test would record this test as an XPASS failure (i.e., an unexpected success).
@importorskip('PIL')
@importorskip('tkinter')
@skip(reason='"excludedimports" support is non-deterministically broken.')
def test_pil_no_tkinter(pyi_builder):
    """
    Ensure that the Tkinter package excluded by `PIL` package hooks is unimportable by frozen applications explicitly
    importing only the latter.
    """

    pyi_builder.test_source(
        """
        import PIL.Image

        # Dynamically importing the Tkinter package should fail with an "ImportError", implying "PIL" package hooks
        # successfully excluded Tkinter. To prevent PyInstaller from parsing this import and thus freezing this
        # extension with this test, this import is dynamic.
        try:
            __import__('tkinter')
            raise SystemExit('ERROR: Module tkinter is bundled.')
        except ImportError:
            pass

        # Dynamically importing the "_tkinter" shared library should also fail.
        try:
            __import__('_tkinter')
            raise SystemExit('ERROR: Module _tkinter is bundled.')
        except ImportError:
            pass
        """
    )


# The tkinter module may be available for import, but not actually importable due to missing shared libraries.
# Therefore, we need to use `can_import_module`-based skip decorator instead of `@importorskip`.
@importorskip('PIL')
@pytest.mark.skipif(not can_import_module("tkinter"), reason="tkinter cannot be imported.")
def test_pil_tkinter(pyi_builder):
    """
    Ensure that the Tkinter package excluded by `PIL` package hooks is importable by frozen applications explicitly
    importing both.

    == See Also ==

    * PyInstaller [issue #1584](https://github.com/pyinstaller/pyinstaller/issues/1584).
    """

    pyi_builder.test_source(
        """
        import PIL.Image

        # Statically importing the Tkinter package should succeed, implying this importation successfully overrode
        # the exclusion of this package requested by "PIL" package hooks. To ensure PyInstaller parses this import
        # and freezes this package with this test, this import is static.
        try:
            import tkinter
        except ImportError:
            raise SystemExit('ERROR: Module tkinter is NOT bundled.')
        """
    )


@importorskip('PIL')
@importorskip('matplotlib')
def test_pil_no_matplotlib(pyi_builder):
    """
    Ensure that using PIL.Image does not pull in `matplotlib` when the latter is not explicitly imported by the program.
    The import chain in question,
    PIL.Image -> PIL -> PIL.ImageShow -> IPython -> matplotlib_inline.backend_inline -> matplotlib,
    should be broken by the PIL hook excluding IPython.
    """

    pyi_builder.test_source(
        """
        import PIL.Image

        # Use dynamic import of matplotlib to prevent PyInstaller from picking up the import.
        try:
            __import__('matplotlib')
            raise SystemExit('ERROR: matplotlib is bundled.')
        except ImportError:
            pass
        """
    )
