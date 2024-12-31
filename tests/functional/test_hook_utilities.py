# -----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
import subprocess


def test_collect_entry_point(pyi_builder_spec, script_dir, tmp_path):
    """
    Test PyInstaller.utils.hooks.collect_entry_point().

    On adding ``collect_entry_point('pytest11')`` to the spec file, the list of modules exporting the 'pytest11' entry
    point should be same after freezing.
    """
    from PyInstaller.compat import importlib_metadata
    plugins = sorted(i.module for i in importlib_metadata.entry_points(group="pytest11"))

    assert len(plugins), "The pytest11 entry point appears to have moved."

    pyi_builder_spec.test_spec('list_pytest11_entry_point.spec')
    exe = tmp_path / "dist" / "list_pytest11_entry_point" / "list_pytest11_entry_point"

    p = subprocess.run([str(exe)], stdout=subprocess.PIPE, check=True, encoding="utf-8")
    collected_plugins = p.stdout.strip("\n").split("\n")

    assert collected_plugins == plugins
