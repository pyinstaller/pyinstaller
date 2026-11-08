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

def test_issue_4141(pyi_builder, modules_dir):
    extra_path = modules_dir / 'pyi_issue_4141'
    pyi_builder.test_script(
        'pyi_issue_4141.py', app_name="main", run_from_path=True, pyi_args=['--path', str(extra_path)]
    )


def test_5797(pyi_builder):
    """
    Ensure that user overriding os and/or sys (using them as variables) in the global namespace does not affect
    PyInstaller's ctype hooks, installed during bootstrap, which is scenario of the issue #5797.
    """
    pyi_builder.test_source(
        """
        import ctypes

        # Overwrite sys and os in global namespace
        sys = 'watever'
        os = 'something'

        # Use a ctypes.CDLL, which in turn calls _frozen_name() from PyInstaller's ctypes bootstrap hooks.
        try:
            ctypes.CDLL('nonexistent')
        except Exception as e:
            # We expect PyInstallerImportError to be raised
            exception_name = type(e).__name__
            assert exception_name == 'PyInstallerImportError', f"Unexpected exception type: {exception_name}"
        """
    )
