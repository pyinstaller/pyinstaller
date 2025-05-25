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
Functional tests for the Django content management system (CMS).
"""

from PyInstaller.utils.tests import importorskip


@importorskip('django')
def test_django(pyi_builder, monkeypatch, data_dir):
    # Extend sys.path so PyInstaller could find modules from 'tmpdir/django/'.
    monkeypatch.syspath_prepend(str(data_dir))
    # Django uses manage.py as the main script.
    script = data_dir / 'manage.py'
    # Create the exe, run django command 'check' to do basic sanity checking of the executable.
    pyi_builder.test_script(script, app_name='django_site', app_args=['check'])
