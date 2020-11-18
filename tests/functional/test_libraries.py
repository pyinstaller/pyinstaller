# -*- coding: utf-8 -*-
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

# Library imports
# ---------------
import os

# Third-party imports
# -------------------
import pytest
import py

# Local imports
# -------------
from PyInstaller.compat import is_win, is_darwin, is_linux, is_64bits
from PyInstaller.utils.hooks import is_module_satisfies
from PyInstaller.utils.tests import importorskip, xfail, skipif

# :todo: find a way to get this from `conftest` or such
# Directory with testing modules used in some tests.
_MODULES_DIR = py.path.local(os.path.abspath(__file__)).dirpath('modules')
_DATA_DIR = py.path.local(os.path.abspath(__file__)).dirpath('data')


@importorskip('gevent')
def test_gevent(pyi_builder):
    pyi_builder.test_source(
        """
        import gevent
        gevent.spawn(lambda: x)
        """,
        # reduce footprint of the test (and avoid issued introduced by one of
        # these packages breaking)
        excludes=["PySide2", "PyQt5", "numpy", "scipy"])


@importorskip('gevent')
def test_gevent_monkey(pyi_builder):
    pyi_builder.test_source(
        """
        from gevent.monkey import patch_all
        patch_all()
        """,
        # reduce footprint of the test (and avoid issued introduced by one of
        # these packages breaking)
        excludes=["PySide2", "PyQt5", "numpy", "scipy"])


@xfail(is_darwin, reason='Issue #1895.')
def test_tkinter(pyi_builder):
    pyi_builder.test_script('pyi_lib_tkinter.py')


@xfail(is_darwin, reason='Issue #1895.')
@importorskip('FixTk')
def test_tkinter_FixTk(pyi_builder):
    # check if Tkinter includes FixTk
    # TODO: Python 3 contains module
    #  'tkinter._fix' - does it need any special test or handling?
    # TODO: How does the following code check if FixTk is included?
    pyi_builder.test_source("""
    import tkinter
    """)


def test_pkg_resource_res_string(pyi_builder, monkeypatch):
    # Include some data files for testing pkg_resources module.
    datas = os.pathsep.join((str(_MODULES_DIR.join('pkg3', 'sample-data.txt')),
                             'pkg3'))
    pyi_builder.test_script('pkg_resource_res_string.py',
                            pyi_args=['--add-data', datas])


def test_pkgutil_get_data(pyi_builder, monkeypatch):
    # Include some data files for testing pkg_resources module.
    datas = os.pathsep.join((str(_MODULES_DIR.join('pkg3', 'sample-data.txt')),
                             'pkg3'))
    pyi_builder.test_script('pkgutil_get_data.py',
                            pyi_args=['--add-data', datas])


@xfail(
    reason='Our import mechanism returns the wrong loader-class for __main__.'
)
def test_pkgutil_get_data__main__(pyi_builder, monkeypatch):
    # Include some data files for testing pkg_resources module.
    datas = os.pathsep.join((str(_MODULES_DIR.join('pkg3', 'sample-data.txt')),
                             'pkg3'))
    pyi_builder.test_script('pkgutil_get_data__main__.py',
                            pyi_args=['--add-data', datas])


@importorskip('sphinx')
def test_sphinx(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test
    pyi_builder.test_script('pyi_lib_sphinx.py')


@importorskip('pygments')
def test_pygments(pyi_builder):
    pyi_builder.test_source(
        """
        # This sample code is taken from http://pygments.org/docs/quickstart/.
        from pygments import highlight
        from pygments.lexers import PythonLexer
        from pygments.formatters import HtmlFormatter

        code = 'print "Hello World"'
        print(highlight(code, PythonLexer(), HtmlFormatter()))
        """)


PYQT5_NEED_OPENGL = pytest.mark.skipif(is_module_satisfies('PyQt5 <= 5.10.1'),
    reason='PyQt5 v5.10.1 and older does not package ``opengl32sw.dll``, the '
    'OpenGL software renderer, which this test requires.')


# Parametrize test to run the same basic code on both Python Qt libraries.
QtPyLibs = pytest.mark.parametrize('QtPyLib', ['PyQt5', 'PySide2'])

# OS X bundles, produced by the ``--windowed`` flag, invoke a unique code path
# that sometimes causes failures in Qt applications.
USE_WINDOWED_KWARG = dict(pyi_args=['--windowed']) if is_darwin else {}


# Define a function to remove paths with ``path_to_clean`` in them during a
# test so that PyQt5/PySide2 tests pass. Only remove them in Windows, since
# Mac/Linux Qt libraries don't rely on the path to find libraries.
def path_clean(monkeypatch, path_to_clean):
    if is_win:
        # Eliminate the other library from the path.
        path_to_clean = dict(PyQt5='PySide2', PySide2='PyQt5')[path_to_clean]
        new_path = os.pathsep.join(
            [x for x in os.environ['PATH'].split(os.pathsep)
             if path_to_clean not in x]
        )
        monkeypatch.setenv('PATH', new_path)


@PYQT5_NEED_OPENGL
@importorskip('PyQt5')
def test_PyQt5_uic(tmpdir, pyi_builder, data_dir, monkeypatch):
    path_clean(monkeypatch, 'PyQt5')
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_PyQt5-uic.py')


# Produce the source code for QWebEngine tests by inserting the path of an HTML
# page to display.
def get_QWebEngine_html(qt_flavor, data_dir):
    return """
        from {0}.QtWidgets import QApplication
        from {0}.QtWebEngineWidgets import QWebEngineView
        from {0}.QtCore import QUrl, QTimer

        app = QApplication([])
        view = QWebEngineView()
        view.load(QUrl.fromLocalFile({1}))
        view.show()
        view.page().loadFinished.connect(
            # Display the web page for one second after it loads.
            lambda ok: QTimer.singleShot(1000, app.quit))
        app.exec_()
        """.format(qt_flavor,
                   # Use repr to avoid accidental special characters in Windows
                   # filenames: ``c:\temp`` is ``c<tab>emp``!
                   repr(data_dir.join('test_web_page.html').strpath))


@xfail(is_linux, reason='See issue #4666')
@pytest.mark.skipif(is_win and not is_64bits, reason="Qt 5.11+ for Windows "
    "only provides pre-compiled Qt WebEngine binaries for 64-bit processors.")
@pytest.mark.skipif(is_module_satisfies('PyQt5 == 5.11.3') and is_darwin,
    reason='This version of the OS X wheel does not include QWebEngine.')
@importorskip('PyQt5')
def test_PyQt5_QWebEngine(pyi_builder, data_dir, monkeypatch):
    path_clean(monkeypatch, 'PyQt5')
    if is_darwin:
        # This tests running the QWebEngine on OS X. To do so, the test must:
        #
        # 1. Run only a onedir build -- onefile builds don't work.
        if pyi_builder._mode != 'onedir':
            pytest.skip('The QWebEngine .app bundle '
                        'only supports onedir mode.')

        # 2. Only test the Mac .app bundle, by modifying the executes this
        #    fixture runs.
        _old_find_executables = pyi_builder._find_executables
        # Create a replacement method that selects just the .app bundle.

        def _replacement_find_executables(self, name):
            path_to_onedir, path_to_app_bundle = _old_find_executables(name)
            return [path_to_app_bundle]
        # Use this in the fixture. See https://stackoverflow.com/a/28060251 and
        # https://docs.python.org/3/howto/descriptor.html.
        pyi_builder._find_executables = \
            _replacement_find_executables.__get__(pyi_builder)

    # 3. Run the test with specific command-line arguments. Otherwise, OS X
    # builds fail. Also use this for the Linux and Windows builds, since this is
    # a common case.
    pyi_builder.test_source(get_QWebEngine_html('PyQt5', data_dir),
                            **USE_WINDOWED_KWARG)


@PYQT5_NEED_OPENGL
@QtPyLibs
def test_Qt5_QtQml(pyi_builder, QtPyLib, monkeypatch):
    path_clean(monkeypatch, QtPyLib)
    pytest.importorskip(QtPyLib)

    pyi_builder.test_source(
        """
        import sys

        from {0}.QtGui import QGuiApplication
        from {0}.QtQml import QQmlApplicationEngine
        from {0}.QtCore import QTimer, QUrl

        # Select a style via the `command line <https://doc.qt.io/qt-5/qtquickcontrols2-styles.html#command-line-argument>`_,
        # since currently PyQt5 doesn't `support https://riverbankcomputing.com/pipermail/pyqt/2018-March/040180.html>`_
        # ``QQuickStyle``. Using this style with the QML below helps to verify
        # that all QML files are packaged; see https://github.com/pyinstaller/pyinstaller/issues/3711.
        app = QGuiApplication(sys.argv + ['-style', 'imagine'])
        engine = QQmlApplicationEngine()
        engine.loadData(b'''
            import QtQuick 2.11
            import QtQuick.Controls 2.4

            ApplicationWindow {{
                visible: true
                ProgressBar {{value: 0.6}}
            }}
            ''', QUrl())

        if not engine.rootObjects():
            sys.exit(-1)

        # Exit Qt when the main loop becomes idle.
        QTimer.singleShot(0, app.exit)

        res = app.exec_()
        del engine
        sys.exit(res)
        """.format(QtPyLib), **USE_WINDOWED_KWARG)


@pytest.mark.parametrize('QtPyLib', [
    'PyQt5',
    pytest.param(
        'PySide2',
        marks=xfail(is_win, reason='PySide2 SSL hook needs updating.')
    )
])
def test_Qt5_SSL_support(pyi_builder, monkeypatch, QtPyLib):
    path_clean(monkeypatch, QtPyLib)
    pytest.importorskip(QtPyLib)

    pyi_builder.test_source(
        """
        from PyQt5.QtNetwork import QSslSocket
        assert QSslSocket.supportsSsl()
        """, **USE_WINDOWED_KWARG)


# Test that the ``PyQt5.Qt`` module works by importing something from it.
#
# The Qt Bluetooth API (which any import to ``PyQt5.Qt`` implicitly imports)
# isn't compatible with Windows Server 2012 R2, the OS Appveyor runs.
# Specifically, running on Server 2012 causes the test to display an error in
# `a dialog box <https://github.com/mindfulness-at-the-computer/mindfulness-at-the-computer/issues/234>`_.
# The alternative of using a newer Appveyor OS `fails <https://github.com/pyinstaller/pyinstaller/pull/3563>`_.
# Therefore, skip this test on Appveyor by testing for one of its `environment
# variables <https://www.appveyor.com/docs/environment-variables/>`_.
@skipif(os.environ.get('APPVEYOR') == 'True',
        reason='The Appveyor OS is incompatible with PyQt.Qt.')
@importorskip('PyQt5')
@pytest.mark.skipif(is_module_satisfies('PyQt5 == 5.11.3') and is_darwin,
    reason='This version of the OS X wheel does not include QWebEngine.')
def test_PyQt5_Qt(pyi_builder, monkeypatch):
    path_clean(monkeypatch, 'PyQt5')
    pyi_builder.test_source('from PyQt5.Qt import QLibraryInfo',
                            **USE_WINDOWED_KWARG)


@QtPyLibs
def test_Qt5_QTranslate(pyi_builder, monkeypatch, QtPyLib):
    path_clean(monkeypatch, QtPyLib)
    pytest.importorskip(QtPyLib)
    pyi_builder.test_source(
        """
        from {0}.QtWidgets import QApplication
        from {0}.QtCore import (
            QTranslator,
            QLocale,
            QLibraryInfo,
        )

        # Initialize Qt default translations
        app = QApplication([])
        translator = QTranslator()
        locale = QLocale('de_DE')
        translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)

        print('Qt locale path: %s' % translation_path)

        if translator.load(locale, "qtbase_", directory=translation_path):
            print('Qt locale %s loaded.' % locale.name())
        else:
            print('Qt locale %s not found!' % locale.name())
            assert False
        """.format(QtPyLib))


@importorskip('PySide2')
def test_PySide2_QWebEngine(pyi_builder, data_dir):
    if is_darwin:
        # QWebEngine on OS X only works with a onedir build -- onefile builds
        # don't work. Skip the test execution for onefile builds.
        if pyi_builder._mode != 'onedir':
            pytest.skip('The QWebEngine .app bundle '
                        'only supports onedir mode.')

    pyi_builder.test_source(get_QWebEngine_html('PySide2', data_dir),
                            **USE_WINDOWED_KWARG)


@importorskip('zope.interface')
def test_zope_interface(pyi_builder):
    # Tests that `nspkg.pth`-based namespace package are bundled properly.
    # The `nspkg.pth` file is created by setuptools and thus changes
    # frequently. If this test fails most propably
    # _SETUPTOOLS_NAMESPACEPKG_PTHs in modulegraph needs to be updated.
    pyi_builder.test_source(
        """
        # Package 'zope' does not contain __init__.py file.
        # Just importing 'zope.interface' is sufficient.
        import zope.interface
        """)


@importorskip('idlelib')
def test_idlelib(pyi_builder):
    pyi_builder.test_source(
        """
        # This file depends on loading some icons, located based on __file__.
        try:
            import idlelib.TreeWidget
        except:
            import idlelib.tree
        """)


@importorskip('keyring')
def test_keyring(pyi_builder):
    pyi_builder.test_source("import keyring")


@importorskip('numpy')
def test_numpy(pyi_builder):
    pyi_builder.test_source(
        """
        import numpy
        from numpy.core.numeric import dot
        print('dot(3, 4):', dot(3, 4))
        """)


@importorskip('pytz')
def test_pytz(pyi_builder):
    pyi_builder.test_source(
        """
        import pytz
        pytz.timezone('US/Eastern')
        """)


@importorskip('requests')
def test_requests(tmpdir, pyi_builder, data_dir, monkeypatch):
    # Note that including the data_dir fixture copies files needed by this test.
    # Include the data files.
    datas = os.pathsep.join((str(data_dir.join('*')), os.curdir))
    pyi_builder.test_script('pyi_lib_requests.py',
                            pyi_args=['--add-data', datas])


@importorskip('urllib3.packages.six')
def test_urllib3_six(pyi_builder):
    # Test for pre-safe-import urllib3.packages.six.moves.
    pyi_builder.test_source("""
        import urllib3.connectionpool
        import types
        assert isinstance(urllib3.connectionpool.queue, types.ModuleType)
        """)


@importorskip('sqlite3')
def test_sqlite3(pyi_builder):
    pyi_builder.test_source(
        """
        # PyInstaller did not included module 'sqlite3.dump'.
        import sqlite3
        conn = sqlite3.connect(':memory:')
        csr = conn.cursor()
        csr.execute('CREATE TABLE Example (id)')
        for line in conn.iterdump():
             print(line)
        """)


# Note that @importorskip('scapy') isn't sufficient; this doesn't ask scapy to
# import its backend dependencies (such as pcapy or dnet). scapy.all does import
# the backends, skipping this test if they aren't installed.
@importorskip('scapy.all')
def test_scapy(pyi_builder):
    pyi_builder.test_source(
        """
        # Test-cases taken from issue #834
        import scapy.all
        scapy.all.IP

        from scapy.all import IP

        # Test-case taken from issue #202.
        from scapy.all import *
        DHCP # scapy.layers.dhcp.DHCP
        BOOTP # scapy.layers.dhcp.BOOTP
        DNS # scapy.layers.dns.DNS
        ICMP # scapy.layers.inet.ICMP
        """)


@importorskip('scapy.all')
def test_scapy2(pyi_builder):
    pyi_builder.test_source(
        """
        # Test the hook to scapy.layers.all
        from scapy.layers.all import DHCP
        """)


@importorskip('scapy.all')
def test_scapy3(pyi_builder):
    pyi_builder.test_source(
        """
        # Test whether
        # a) scapy packet layers are not included if neither scapy.all nor
        #    scapy.layers.all are imported.
        # b) packages are included if imported explicitly

        # This test-case assumes, that layer modules are imported only if
        NAME = 'hook-scapy.layers.all'
        layer_inet = 'scapy.layers.inet'

        def testit():
            try:
                __import__(layer_inet)
                raise SystemExit('Self-test of hook %s failed: package module found'
                                 % NAME)
            except ImportError, e:
                if not e.args[0].endswith(' inet'):
                    raise SystemExit('Self-test of hook %s failed: package module found'
                                    ' and has import errors: %r' % (NAME, e))

        import scapy
        testit()
        import scapy.layers
        testit()
        # Explicitly import a single layer module. Note: This module MUST NOT
        # import inet (neither directly nor indirectly), otherwise the test
        # above fails.
        import scapy.layers.ir
        """)


@importorskip('sqlalchemy')
def test_sqlalchemy(pyi_builder):
    pyi_builder.test_source(
        """
        # The hook behaviour is to include with sqlalchemy all installed database
        # backends.
        import sqlalchemy
        # This import was known to fail with sqlalchemy 0.9.1
        import sqlalchemy.ext.declarative
        """)


@importorskip('twisted')
def test_twisted(pyi_builder):
    pyi_builder.test_source(
        """
        # Twisted is an event-driven networking engine.
        #
        # The 'reactor' is object that starts the eventloop.
        # There are different types of platform specific reactors.
        # Platform specific reactor is wrapped into twisted.internet.reactor module.
        from twisted.internet import reactor
        # Applications importing module twisted.internet.reactor might fail
        # with error like:
        #
        #     AttributeError: 'module' object has no attribute 'listenTCP'
        #
        # Ensure default reactor was loaded - it has method 'listenTCP' to start server.
        if not hasattr(reactor, 'listenTCP'):
            raise SystemExit('Twisted reactor not properly initialized.')
        """)


@importorskip('pyexcelerate')
def test_pyexcelerate(pyi_builder):
    pyi_builder.test_source(
        """
        # Requires PyExcelerate 0.6.1 or higher
        # Tested on Windows 7 x64 SP1 with CPython 2.7.6
        import pyexcelerate
        """)


@importorskip('usb')
@pytest.mark.skipif(is_linux, reason='libusb_exit segfaults on some linuxes')
def test_usb(pyi_builder):
    # See if the usb package is supported on this platform.
    try:
        import usb
        # This will verify that the backend is present; if not, it will
        # skip this test.
        usb.core.find()
    except (ImportError, usb.core.NoBackendError):
        pytest.skip('USB backnd not found.')

    pyi_builder.test_source(
        """
        import usb.core
        # NoBackendError fails the test if no backends are found.
        usb.core.find()
        """)


@importorskip('zeep')
def test_zeep(pyi_builder):
    pyi_builder.test_source(
        """
        # Test the hook to zeep
        from zeep import utils
        utils.get_version()
        """)


@importorskip('PIL')
#@pytest.mark.xfail(reason="Fails with Pillow 3.0.0")
def test_pil_img_conversion(pyi_builder):
    datas = os.pathsep.join((str(_DATA_DIR.join('PIL_images')), '.'))
    pyi_builder.test_script(
        'pyi_lib_PIL_img_conversion.py',
        pyi_args=['--add-data', datas,
                  # Use console mode or else on Windows the VS() messageboxes
                  # will stall pytest.
                  '--console'])


@xfail(is_darwin, reason='Issue #1895.')
@importorskip('PIL')
@importorskip('FixTk')
def test_pil_FixTk(pyi_builder):
    # hook-PIL is excluding FixTk, but is must still be included
    # since it is imported elsewhere. Also see issue #1584.
    pyi_builder.test_source("""
    import tkinter
    import FixTk, PIL
    """)

@importorskip('PIL.ImageQt')
@importorskip('PyQt5')
def test_pil_PyQt5(pyi_builder):
    # hook-PIL is excluding PyQt5, but is must still be included
    # since it is imported elsewhere. Also see issue #1584.
    pyi_builder.test_source("""
    import PyQt5
    import PIL
    import PIL.ImageQt
    """)


@importorskip('PIL')
def test_pil_plugins(pyi_builder):
    pyi_builder.test_source(
        """
        # Verify packaging of PIL.Image. Specifically, the hidden import of FixTk
        # importing tkinter is causing some problems.
        from PIL.Image import frombytes
        print(frombytes)

        # PIL import hook should bundle all available PIL plugins. Verify that plugins
        # are bundled.
        from PIL import Image
        Image.init()
        MIN_PLUG_COUNT = 7  # Without all plugins the count is usually 6.
        plugins = list(Image.SAVE.keys())
        plugins.sort()
        if len(plugins) < MIN_PLUG_COUNT:
            raise SystemExit('No PIL image plugins were bundled!')
        else:
            print('PIL supported image formats: %s' % plugins)
        """)


@importorskip('pandas')
def test_pandas_extension(pyi_builder):
    # Tests that the C extension ``pandas._libs.lib`` is properly bundled. Issue #1580.
    # See http://pandas.pydata.org/pandas-docs/stable/whatsnew.html#modules-privacy-has-changed.
    pyi_builder.test_source(
        """
        from pandas._libs.lib import is_float
        assert is_float(1) == 0
        """)

