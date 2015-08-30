#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Library imports
# ---------------
import os
import pytest
import shutil

# Local imports
# -------------
from PyInstaller.compat import is_win
from PyInstaller.utils.tests import importorskip, xfail_py2


@xfail_py2
@importorskip('django')
# Django test might sometimes hang.
@pytest.mark.timeout(timeout=7*60)
def test_django(pyi_builder, monkeypatch, data_dir):
    script_dir = os.path.join(data_dir, 'django_site')
    # Extend sys.path so PyInstaller could find modules from 'django_site' project.
    monkeypatch.syspath_prepend(script_dir)
    # Django uses manage.py as the main script.
    script = os.path.join(script_dir, 'manage.py')
    # Create the exe, run django command 'check' to do basic sanity checking of the
    # executable.
    pyi_builder.test_script(script, app_name='django_site', app_args=['check'])


def test_tkinter(pyi_builder):
    pyi_builder.test_script('pyi_lib_tkinter.py')


@importorskip('zmq')
def test_zmq(pyi_builder):
    pyi_builder.test_script('pyi_lib_zmq.py')


@importorskip('sphinx')
def test_sphinx(tmpdir, pyi_builder, data_dir):
    # Copy the data/sphix directory to the tempdir used by this test.
    shutil.copytree(os.path.join(data_dir, 'sphinx'),
                    os.path.join(tmpdir.strpath, 'data', 'sphinx'))
    pyi_builder.test_script('pyi_lib_sphinx.py')

@pytest.mark.xfail(reason='pkg_resources is not supported yet.')
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

@pytest.mark.xfail(reason='Reports "ImportError: No module named QtWebKit.QWebView".')
@importorskip('PyQt4')
def test_PyQt4_uic(tmpdir, pyi_builder, data_dir):
    # Copy the data/PyQt4-uic.ui file to the tempdir used by this test.
    os.mkdir(os.path.join(tmpdir.strpath, 'data'))
    shutil.copy(os.path.join(data_dir, 'PyQt4-uic.ui'),
                os.path.join(tmpdir.strpath, 'data'))

    pyi_builder.test_script('pyi_lib_PyQt4-uic.py')


@importorskip('zope.interface')
def test_zope_interface(pyi_builder):
    # Tests that modules without __init__.py file are bundled properly.
    pyi_builder.test_source(
        """
        # Package 'zope' does not contain __init__.py file.
        # Just importing 'zope.interface' is sufficient.
        import zope.interface
        """)
