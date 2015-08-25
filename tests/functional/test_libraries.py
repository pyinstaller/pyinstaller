#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import pytest

from PyInstaller.compat import is_win
from PyInstaller.utils.tests import importorskip, xfail_py2
from tests.functional.data_dir import DATA_DIR


@xfail_py2
@importorskip('django')
# Django test might sometimes hang.
@pytest.mark.timeout(timeout=7*60)
def test_django(pyi_builder, monkeypatch):
    script_dir = os.path.join(DATA_DIR, 'django_site')
    # Extend sys.path so PyInstaller could find modules from 'django_site' project.
    monkeypatch.syspath_prepend(script_dir)
    # Django uses manage.py as the main script.
    script = os.path.join(script_dir, 'manage.py')
    # Create the exe, run django command 'check' to do basic sanity checking of the
    # executable.
    pyi_builder.test_script(script, app_name='django_site', app_args=['check'])


@pytest.mark.xfail(is_win, reason='onefile mode known to fail on Windows')
def test_tkinter(pyi_builder):
    pyi_builder.test_script('pyi_lib_tkinter.py')


@pytest.mark.xfail(is_win, reason='known to fail in Appveyor for unknown reason.')
@importorskip('zmq')
def test_zmq(pyi_builder):
    pyi_builder.test_script('pyi_lib_zmq.py')

@importorskip('sphinx')
def test_sphinx(pyi_builder):
    pyi_builder.test_script('pyi_lib_sphinx.py', app_args=[DATA_DIR])

@importorskip('pylint')
def test_pylint(pyi_builder):
    pyi_builder.test_script('pyi_lib_pylint.py')

@importorskip('pygments')
def test_pygments(pyi_builder):
    pyi_builder.test_script('pyi_lib_pygments.py')

@importorskip('markdown')
def test_markdown(pyi_builder):
    pyi_builder.test_script('pyi_lib_markdown.py')

@importorskip('PyQt4')
def test_PyQt4_QtWebKit(pyi_builder):
    pyi_builder.test_script('pyi_lib_PyQt4-QtWebKit.py')

@importorskip('PyQt4')
def test_PyQt4_uic(pyi_builder):
    pyi_builder.test_script('pyi_lib_PyQt4-uic.py', app_args=[DATA_DIR])

