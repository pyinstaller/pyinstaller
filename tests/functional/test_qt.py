# -*- coding: utf-8 -*-
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

import os

import pytest

from PyInstaller.compat import is_win, is_darwin, is_linux, is_64bits
from PyInstaller.utils.hooks import is_module_satisfies
from PyInstaller.utils.tests import importorskip, xfail, skipif


PYQT5_NEED_OPENGL = pytest.mark.skipif(
    is_module_satisfies('PyQt5 <= 5.10.1'),
    reason='PyQt5 v5.10.1 and older does not package ``opengl32sw.dll``, '
    'the OpenGL software renderer, which this test requires.')


# Parametrize test to run the same basic code on both Python Qt libraries.
QtPyLibs = pytest.mark.parametrize('QtPyLib', ['PyQt5', 'PyQt6',
                                               'PySide2', 'PySide6'])

# OS X bundles, produced by the ``--windowed`` flag, invoke a unique code path
# that sometimes causes failures in Qt applications.
USE_WINDOWED_KWARG = dict(pyi_args=['--windowed']) if is_darwin else {}


# Clean up PATH so that of all potentially installed Qt-based packages
# (PyQt5, PyQt6, PySide2, and PySide6), only the Qt shared libraries of
# the specified package (namespace) remain in the PATH.
# This is necessary to prevent DLL interference in tests when multiple
# Qt-based packages are installed. Applicable only on Windows, as on
# other OSes the Qt shared library path(s) are not added to PATH.
def _qt_dll_path_clean(monkeypatch, namespace):
    if not is_win:
        return

    # Remove all other Qt5/6 bindings from PATH
    all_namespaces = {'PyQt5', 'PyQt6', 'PySide2', 'PySide6'}
    all_namespaces.discard(namespace)
    new_path = os.pathsep.join(
        [x for x in os.environ['PATH'].split(os.pathsep)
         if not any(ns in x for ns in all_namespaces)]
    )
    monkeypatch.setenv('PATH', new_path)


@QtPyLibs
def test_Qt_QtWidgets(pyi_builder, QtPyLib, monkeypatch):
    _qt_dll_path_clean(monkeypatch, QtPyLib)
    pytest.importorskip(QtPyLib)

    pyi_builder.test_source(
        """
        import sys

        from {0}.QtWidgets import QApplication, QWidget
        from {0}.QtCore import QTimer

        is_qt6 = '{0}' in {{'PySide6', 'PyQt6'}}

        app = QApplication(sys.argv)
        window = QWidget()
        window.setWindowTitle('Hello world!')
        window.show()

        # Exit Qt when the main loop becomes idle.
        QTimer.singleShot(0, app.exit)

        if is_qt6:
            # Qt6: exec_() is deprecated in PySide6 and removed from
            # PyQt6 in favor of exec()
            res = app.exec()
        else:
            res = app.exec_()
        sys.exit(res)
        """.format(QtPyLib), **USE_WINDOWED_KWARG)


@PYQT5_NEED_OPENGL
@QtPyLibs
def test_Qt_QtQml(pyi_builder, QtPyLib, monkeypatch):
    _qt_dll_path_clean(monkeypatch, QtPyLib)
    pytest.importorskip(QtPyLib)

    pyi_builder.test_source(
        """
        import sys

        from {0}.QtGui import QGuiApplication
        from {0}.QtQml import QQmlApplicationEngine
        from {0}.QtCore import QTimer, QUrl

        is_qt6 = '{0}' in {{'PyQt6', 'PySide6'}}

        # Select a style via the `command line
        # <https://doc.qt.io/qt-5/qtquickcontrols2-styles.html#command-line-argument>`_,
        # as PyQt5 currently does not `support
        # https://riverbankcomputing.com/pipermail/pyqt/2018-March/040180.html>`_
        # ``QQuickStyle``. Using this style with the QML below helps to verify
        # that all QML files are packaged; see
        # https://github.com/pyinstaller/pyinstaller/issues/3711.
        #
        # In Qt5, the style name is lower case ('imagine'), whereas
        # in Qt6, it is capitalized ('Imagine')
        app = QGuiApplication(sys.argv +
            ['-style', 'Imagine' if is_qt6 else 'imagine'])
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

        if is_qt6:
            # Qt6: exec_() is deprecated in PySide6 and removed from
            # PyQt6 in favor of exec()
            res = app.exec()
        else:
            res = app.exec_()
        del engine
        sys.exit(res)
        """.format(QtPyLib), **USE_WINDOWED_KWARG)


@pytest.mark.parametrize('QtPyLib', [
    'PyQt5',
    'PyQt6',
    pytest.param(
        'PySide2',
        marks=xfail(is_win, reason='PySide2 wheels on Windows do not '
                                   'include SSL DLLs.')),
    pytest.param(
        'PySide6',
        marks=xfail(is_win, reason='PySide6 wheels on Windows do not '
                                   'include SSL DLLs.')),
])
def test_Qt_QtNetwork_SSL_support(pyi_builder, monkeypatch, QtPyLib):
    _qt_dll_path_clean(monkeypatch, QtPyLib)
    pytest.importorskip(QtPyLib)

    pyi_builder.test_source(
        """
        from {0}.QtNetwork import QSslSocket
        assert QSslSocket.supportsSsl()
        """.format(QtPyLib), **USE_WINDOWED_KWARG)


@QtPyLibs
def test_Qt_QTranslate(pyi_builder, monkeypatch, QtPyLib):
    _qt_dll_path_clean(monkeypatch, QtPyLib)
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
        if hasattr(QLibraryInfo, 'path'):
            # Qt6
            translation_path = QLibraryInfo.path(
                QLibraryInfo.LibraryPath.TranslationsPath)
        else:
            # Qt5
            translation_path = QLibraryInfo.location(
                QLibraryInfo.TranslationsPath)

        print('Qt locale path: %s' % translation_path)

        if translator.load(locale, "qtbase_", directory=translation_path):
            print('Qt locale %s loaded.' % locale.name())
        else:
            print('Qt locale %s not found!' % locale.name())
            assert False
        """.format(QtPyLib))


# Test that the ``PyQt5.Qt`` module works by importing something from it.
#
# NOTE: the ``PyQt5.Qt`` consolidating module is specific to PyQt5. It
# is not present in either PySide2 nor PySide6, and its consolidating
# behavior has been removed in PyQt6.
#
# The Qt Bluetooth API (which any import to ``PyQt5.Qt`` implicitly imports)
# isn't compatible with Windows Server 2012 R2, the OS Appveyor runs.
# Specifically, running on Server 2012 causes the test to display an error in
# `a dialog box
# <https://github.com/mindfulness-at-the-computer/mindfulness-at-the-computer/issues/234>`_.
# The alternative of using a newer Appveyor OS `fails
# <https://github.com/pyinstaller/pyinstaller/pull/3563>`_.
# Therefore, skip this test on Appveyor by testing for one of its `environment
# variables <https://www.appveyor.com/docs/environment-variables/>`_.
@skipif(os.environ.get('APPVEYOR') == 'True',
        reason='The Appveyor OS is incompatible with PyQt.Qt.')
@importorskip('PyQt5')
@pytest.mark.skipif(is_module_satisfies('PyQt5 == 5.11.3') and is_darwin,
                    reason='This version of the OS X wheel does not '
                           'include QWebEngine.')
def test_PyQt5_Qt(pyi_builder, monkeypatch):
    _qt_dll_path_clean(monkeypatch, 'PyQt5')
    pyi_builder.test_source('from PyQt5.Qt import QLibraryInfo',
                            **USE_WINDOWED_KWARG)


@PYQT5_NEED_OPENGL
@importorskip('PyQt5')
def test_PyQt5_uic(tmpdir, pyi_builder, data_dir, monkeypatch):
    _qt_dll_path_clean(monkeypatch, 'PyQt5')
    # Note that including the data_dir fixture copies files needed by
    # this test.
    pyi_builder.test_script('pyi_lib_PyQt5-uic.py')


# QtWebEngine test. This module is specific to PyQt5 and PySide2, as
# it has not been ported to Qt6 yet (as of Qt6 6.1.0)

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
@pytest.mark.skipif(is_win and not is_64bits,
                    reason="Qt 5.11+ for Windows only provides pre-compiled "
                           "Qt WebEngine binaries for 64-bit processors.")
@pytest.mark.skipif(is_module_satisfies('PyQt5 == 5.11.3') and is_darwin,
                    reason='This version of the OS X wheel does not '
                           'include QWebEngine.')
@importorskip('PyQt5')
def test_PyQt5_QWebEngine(pyi_builder, data_dir, monkeypatch):
    _qt_dll_path_clean(monkeypatch, 'PyQt5')
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
    # builds fail. Also use this for the Linux and Windows builds, since this
    # is a common case.
    pyi_builder.test_source(get_QWebEngine_html('PyQt5', data_dir),
                            **USE_WINDOWED_KWARG)


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
