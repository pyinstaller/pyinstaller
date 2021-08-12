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
Functional tests for the Django content management system (CMS).
"""

import pytest

from PyInstaller.compat import is_win, is_py37
from PyInstaller.utils.tests import importorskip, xfail


# In Django 2.1, ``django/contrib/auth/password_validation.py``, line 168, which is
#
#   ``DEFAULT_PASSWORD_LIST_PATH = Path(__file__).resolve().parent / 'common-passwords.txt.gz'``,
#
# the call to ``resolve()`` causes Python 3.5 to raise an exception that ``password_validation.pyc`` does not exist.
# Python 3.6 added the default argument ``strict=False``, which ignores this exception. This file is in the archive, but
# not the filesystem.
@importorskip('django')
# Import error occurs on win/py37
@xfail(is_win and is_py37, reason='Fails on win/py37.')
# Django test might sometimes hang.
@pytest.mark.timeout(timeout=7 * 60)
def test_django(pyi_builder, monkeypatch, data_dir):
    # Extend sys.path so PyInstaller could find modules from 'tmpdir/django/'.
    monkeypatch.syspath_prepend(data_dir.strpath)
    # Django uses manage.py as the main script.
    script = str(data_dir / 'manage.py')
    # Create the exe, run django command 'check' to do basic sanity checking of the executable.
    pyi_builder.test_script(script, app_name='django_site', app_args=['check'])
