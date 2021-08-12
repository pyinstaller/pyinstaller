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

from PyInstaller.utils.tests import importorskip


@importorskip('pkg_resources')
def test_pkg_resources_importable(pyi_builder):
    """
    Check that a trivial example using pkg_resources does build.
    """
    pyi_builder.test_source("""
        import pkg_resources
        pkg_resources.working_set.require()
        """)
