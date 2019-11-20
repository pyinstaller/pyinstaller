#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils.tests import importorskip

@importorskip('pkg_resources')
def test_pkg_resources_importable(pyi_builder):
    """
    Check that a trivial example using pkg_resources does build.
    """
    pyi_builder.test_source(
        """
        import pkg_resources
        pkg_resources.working_set.require()
        """)
