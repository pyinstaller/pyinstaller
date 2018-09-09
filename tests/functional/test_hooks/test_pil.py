#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional tests for the Python Imaging Library (PIL).

Note that the original unmaintained PIL has been obsoleted by the PIL-compatible
fork Pillow, which retains the same Python package `PIL`.
"""

from PyInstaller.compat import modname_tkinter, is_darwin
from PyInstaller.utils.tests import importorskip, skip, xfail


# "excludedimports" support is currently non-deterministic and hence cannot be
# marked as @xfail. If this test were marked as @xfail but succeeded, py.test
# would record this test as an XPASS failure (i.e., an unexpected success).
@importorskip('PIL')
@importorskip(modname_tkinter)
@skip(reason='"excludedimports" support is non-deterministically broken.')
def test_pil_no_tkinter(pyi_builder):
    """
    Ensure that the Tkinter package excluded by `PIL` package hooks is
    unimportable by frozen applications explicitly importing only the latter.
    """

    pyi_builder.test_source("""
        import PIL.Image

        # Dynamically importing the Tkinter package should fail with an
        # "ImportError", implying "PIL" package hooks successfully excluded
        # Tkinter. To prevent PyInstaller from parsing this import and thus
        # freezing this extension with this test, this import is dynamic.
        try:
            __import__('{modname_tkinter}')
            raise SystemExit('ERROR: Module {modname_tkinter} is bundled.')
        except ImportError:
            pass

        # Dynamically importing the "_tkinter" shared library should also fail.
        try:
            __import__('_tkinter')
            raise SystemExit('ERROR: Module _tkinter is bundled.')
        except ImportError:
            pass
        """.format(modname_tkinter=modname_tkinter))


@importorskip('PIL')
@importorskip(modname_tkinter)
@xfail(is_darwin, reason='Issue #1895. Known to fail with macpython - python.org binary.')
def test_pil_tkinter(pyi_builder):
    """
    Ensure that the Tkinter package excluded by `PIL` package hooks is
    importable by frozen applications explicitly importing both.

    == See Also ==

    * PyInstaller [issue #1584](https://github.com/pyinstaller/pyinstaller/issues/1584).
    """

    pyi_builder.test_source("""
        import PIL.Image

        # Statically importing the Tkinter package should succeed, implying this
        # importation successfully overrode the exclusion of this package
        # requested by "PIL" package hooks. To ensure PyInstaller parses this
        # import and freezes this package with this test, this import is static.
        try:
            import {modname_tkinter}
        except ImportError:
            raise SystemExit('ERROR: Module {modname_tkinter} is NOT bundled.')
        """.format(modname_tkinter=modname_tkinter))
