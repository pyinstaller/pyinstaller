#-----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
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

import pathlib

import pytest

from PyInstaller.utils.tests import importorskip
from PyInstaller.utils.hooks import can_import_module

# All tests in this file require PIL
pytestmark = importorskip('PIL')


# Functional test that tries to convert a .tiff image to a .png
def test_pil_image_conversion(pyi_builder, tmp_path):
    pyi_builder.test_source(
        """
        import sys
        import os

        import PIL.Image

        if len(sys.argv) != 3:
            print(f"use: {sys.argv[0]} <input-filename> <output-filename>")
            raise SystemExit(1)

        input_file = sys.argv[1]
        output_file = sys.argv[2]

        image = PIL.Image.open(input_file)
        image.save(output_file)
        """,
        app_args=[
            str(pathlib.Path(__file__).parent / 'data' / 'PIL_images' / 'tinysample.tiff'),
            str(tmp_path / 'converted_tinysample.png'),
        ],
    )


@importorskip('PyQt5')
def test_pil_pyqt5(pyi_builder):
    # hook-PIL is excluding PyQt5, but is must still be included since it is imported elsewhere.
    # Also see issue #1584.
    pyi_builder.test_source("""
        import PyQt5
        import PIL
        import PIL.ImageQt
        """)


def test_pil_plugins(pyi_builder):
    pyi_builder.test_source(
        """
        # Verify packaging of PIL.Image.
        from PIL.Image import frombytes
        print(frombytes)

        # PIL import hook should bundle all available PIL plugins. Verify that plugins are collected.
        from PIL import Image
        Image.init()
        MIN_PLUG_COUNT = 7  # Without all plugins the count is usually 6.
        plugins = list(Image.SAVE.keys())
        plugins.sort()
        if len(plugins) < MIN_PLUG_COUNT:
            raise SystemExit('No PIL image plugins were collected!')
        else:
            print('PIL supported image formats: %s' % plugins)
        """
    )


# The tkinter module may be available for import, but not actually importable due to missing shared libraries.
# Therefore, we need to use `can_import_module`-based skip decorator instead of `@importorskip`.
@pytest.mark.skipif(not can_import_module("tkinter"), reason="tkinter cannot be imported.")
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
