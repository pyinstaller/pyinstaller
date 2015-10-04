#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional tests for the Django content management system (CMS).
"""

import os
import pytest

from PyInstaller.utils.tests import importorskip, xfail  # xfail_py2


# TODO: Replace the second by the first @xfail after fixing this issue. Thanks!
# @xfail_py2
@xfail(reason='See pull request #1393.')
@importorskip('django')
# Django test might sometimes hang.
@pytest.mark.timeout(timeout=7*60)
def test_django(pyi_builder, monkeypatch, data_dir):
    # Extend sys.path so PyInstaller could find modules from 'tmpdir/django/'.
    monkeypatch.syspath_prepend(data_dir.strpath)
    # Django uses manage.py as the main script.
    script = os.path.join(data_dir.strpath, 'manage.py')
    # Create the exe, run django command 'check' to do basic sanity checking of the
    # executable.
    pyi_builder.test_script(script, app_name='django_site', app_args=['check'])
