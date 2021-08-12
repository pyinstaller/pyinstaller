# -*- encoding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

from subprocess import run, PIPE
from os.path import join


def test_collect_entry_point(pyi_builder_spec, script_dir, tmpdir):
    """
    Test PyInstaller.utils.hooks.collect_entry_point().

    On adding ``collect_entry_point('pytest11')`` to the spec file, the list of modules exporting the 'pytest11' entry
    point should be same after freezing.
    """
    import pkg_resources
    plugins = sorted(i.module_name for i in pkg_resources.iter_entry_points("pytest11"))

    assert len(plugins), "The pytest11 entry point appears to have moved."

    pyi_builder_spec.test_spec('list_pytest11_entry_point.spec')
    exe = join(tmpdir, "dist", "list_pytest11_entry_point", "list_pytest11_entry_point")

    p = run([exe], stdout=PIPE, check=True, universal_newlines=True)
    collected_plugins = p.stdout.strip("\n").split("\n")

    assert collected_plugins == plugins
