#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


def test_sentry(pyi_builder):
    """
    Check if sentry builds correctly.
    """
    pyi_builder.test_source(
        """
        import sentry_sdk
        sentry_sdk.init()
        """)
