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

from PyInstaller.compat import is_win, is_darwin
from PyInstaller.utils.hooks import is_module_satisfies
from PyInstaller.utils.hooks.qt import get_qt_library_info
from PyInstaller.utils.tests import requires, xfail, skipif

PYQT5_NEED_OPENGL = pytest.mark.skipif(
    is_module_satisfies('PyQt5 <= 5.10.1'),
    reason='PyQt5 v5.10.1 and older does not package ``opengl32sw.dll``, '
    'the OpenGL software renderer, which this test requires.'
)


def qt_param(qt_flavor, *args, **kwargs):
    """
    A Qt flavour to be used in @pytest.mark.parametrize(). Implicitly skips the test if said flavor is not installed.
    """
    p = pytest.param(qt_flavor, *args, **kwargs)
    return pytest.param(*p.values, marks=(requires(qt_flavor),) + p.marks, id=p.id)


# Parametrize test to run the same basic code on both Python Qt libraries.
_QT_PY_PACKAGES = ['PyQt5', 'PyQt6', 'PySide2', 'PySide6']
QtPyLibs = pytest.mark.parametrize('QtPyLib', [qt_param(i) for i in _QT_PY_PACKAGES])

# OS X bundles, produced by the ``--windowed`` flag, invoke a unique code path that sometimes causes failures in Qt
# applications.
USE_WINDOWED_KWARG = dict(pyi_args=['--windowed']) if is_darwin else {}


# This is an ugly work-around for an even uglier problem on Windows: we need to ensure that each Qt-based package that
# is going to be used in a test is imported wihout ``pytest.monkeypatch`` being active.
#
# The imports used to happen either during test collection (e.g., due to ``@pytest.importorskip`` annotation on the
# test) or during the actual test execution - either due to ``pytest.importorskip()`` call inside the test, or when
# actually building the frozen test application. With the introduction of ``PyInstaller.utils.tests.requires`` that does
# not actually import the package (but rather just checks its availability), the imports happen only within the tests,
# when building the application. This leads to problems if the very first import of the package happens inside the test
# that uses ``pytest.monkeypatch``.
#
# Specifically, when a Qt-based package is imported, it adds the path to its Qt DLLs to PATH (applies only to Windows).
# Therefore, if (first) import happens under ``pytest.monkeypatch``, the PATH modification is lost for subsequent tests
# (that use the same package). This in turn causes incomplete builds of the test programs, because ``pyi_builder`` calls
# PyInstaller's ``pyi_main.run()`` within the test process instead of spawning a separate process.
#
# Therefore, we manually try to import each Qt-based package, to ensure that their first-time import happens outside of
# the ``pytest.monkeypatch``.
def _ensure_qt_packages_are_imported():
    for pkg in _QT_PY_PACKAGES:
        try:
            __import__(pkg)
        except Exception:
            pass


if is_win:
    _ensure_qt_packages_are_imported()  # Applicable only to Windows


# Similarly to the above PATH-related concerns on Windows, we also need to ensure that all QtLibraryInfo structures in
# Qt hook utils are initialized at this point, before the actual tests start. This is to prevent test-order-dependent
# behavior and potential issues, and applies to all platforms.
#
# Some tests (e.g., test_import::test_import_pyqt5_uic_port) may modify search path to fake PyQt5 module, and if that
# test is the point of initialization for the corresponding QtLibraryInfo structure (triggered by hooks' access to
# .version attribute), the structure ends up with invalid data for subsequent tests as well.
#
# Former solution to this problem was clearing QtLibraryInfo.version at the end of pyi_builder() fixture, which triggers
# re-initialization in each test. But as the content of QtLibraryInfo should be immutable (save for the test with fake
# module), it seems better to pre-initialize the structures in order to ensure predictable behavior.
def _ensure_qt_library_info_is_initialized():
    for pkg in _QT_PY_PACKAGES:
        try:
            info = get_qt_library_info(pkg)
            assert info.version  # trigger initialization
        except Exception:
            pass


_ensure_qt_library_info_is_initialized()


# Clean up PATH so that of all potentially installed Qt-based packages (PyQt5, PyQt6, PySide2, and PySide6), only the Qt
# shared libraries of the specified package (namespace) remain in the PATH.
# This is necessary to prevent DLL interference in tests when multiple Qt-based packages are installed. Applicable only
# on Windows, as on other OSes the Qt shared library path(s) are not added to PATH.
def _qt_dll_path_clean(monkeypatch, namespace):
    if not is_win:
        return

    # Remove all other Qt5/6 bindings from PATH
    all_namespaces = set(_QT_PY_PACKAGES)
    all_namespaces.discard(namespace)
    new_path = os.pathsep.join([
        x for x in os.environ['PATH'].split(os.pathsep) if not any(ns in x for ns in all_namespaces)
    ])
    monkeypatch.setenv('PATH', new_path)


@QtPyLibs
def test_Qt_QtWidgets(pyi_builder, QtPyLib, monkeypatch):
    _qt_dll_path_clean(monkeypatch, QtPyLib)

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
            # Qt6: exec_() is deprecated in PySide6 and removed from PyQt6 in favor of exec()
            res = app.exec()
        else:
            res = app.exec_()
        sys.exit(res)
        """.format(QtPyLib), **USE_WINDOWED_KWARG
    )


@PYQT5_NEED_OPENGL
@QtPyLibs
def test_Qt_QtQml(pyi_builder, QtPyLib, monkeypatch):
    _qt_dll_path_clean(monkeypatch, QtPyLib)

    pyi_builder.test_source(
        """
        import sys

        from {0}.QtGui import QGuiApplication
        from {0}.QtQml import QQmlApplicationEngine
        from {0}.QtCore import QTimer, QUrl

        is_qt6 = '{0}' in {{'PyQt6', 'PySide6'}}

        # Select a style via the `command line
        # <https://doc.qt.io/qt-5/qtquickcontrols2-styles.html#command-line-argument>`_,
        # as PyQt5 currently does not `support https://riverbankcomputing.com/pipermail/pyqt/2018-March/040180.html>`_
        # ``QQuickStyle``. Using this style with the QML below helps to verify that all QML files are packaged; see
        # https://github.com/pyinstaller/pyinstaller/issues/3711.
        #
        # In Qt5, the style name is lower case ('imagine'), whereas in Qt6, it is capitalized ('Imagine')
        app = QGuiApplication(sys.argv + ['-style', 'Imagine' if is_qt6 else 'imagine'])
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
            # Qt6: exec_() is deprecated in PySide6 and removed from PyQt6 in favor of exec()
            res = app.exec()
        else:
            res = app.exec_()
        del engine
        sys.exit(res)
        """.format(QtPyLib), **USE_WINDOWED_KWARG
    )


@pytest.mark.parametrize(
    'QtPyLib', [
        qt_param('PyQt5'),
        qt_param('PyQt6'),
        qt_param('PySide2', marks=xfail(is_win, reason='PySide2 wheels on Windows do not include SSL DLLs.')),
        qt_param('PySide6', marks=xfail(is_win, reason='PySide6 wheels on Windows do not include SSL DLLs.')),
    ]
)
def test_Qt_QtNetwork_SSL_support(pyi_builder, monkeypatch, QtPyLib):
    _qt_dll_path_clean(monkeypatch, QtPyLib)

    pyi_builder.test_source(
        """
        from {0}.QtNetwork import QSslSocket
        assert QSslSocket.supportsSsl()
        """.format(QtPyLib), **USE_WINDOWED_KWARG
    )


@QtPyLibs
def test_Qt_QTranslate(pyi_builder, monkeypatch, QtPyLib):
    _qt_dll_path_clean(monkeypatch, QtPyLib)
    pyi_builder.test_source(
        """
        from {0}.QtWidgets import QApplication
        from {0}.QtCore import QTranslator, QLocale, QLibraryInfo

        # Initialize Qt default translations
        app = QApplication([])
        translator = QTranslator()
        locale = QLocale('de_DE')
        if hasattr(QLibraryInfo, 'path'):
            # Qt6
            translation_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        else:
            # Qt5
            translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)

        print('Qt locale path: %s' % translation_path)

        if translator.load(locale, "qtbase_", directory=translation_path):
            print('Qt locale %s loaded.' % locale.name())
        else:
            print('Qt locale %s not found!' % locale.name())
            assert False
        """.format(QtPyLib)
    )


@PYQT5_NEED_OPENGL
@QtPyLibs
def test_Qt_Ui_file(tmpdir, pyi_builder, data_dir, monkeypatch, QtPyLib):
    _qt_dll_path_clean(monkeypatch, QtPyLib)
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_source(
        """
        import os

        import {0}.QtQuickWidgets  # Used instead of hiddenimports

        from {0}.QtWidgets import QApplication, QWidget
        from {0}.QtCore import QTimer

        from pyi_get_datadir import get_data_dir

        is_qt6 = '{0}' in {{'PyQt6', 'PySide6'}}
        is_pyqt = '{0}' in {{'PyQt5', 'PyQt6'}}

        app = QApplication([])

        # In Qt6, QtQuick supports multiple render APIs and automatically selects one.
        # However, QtQuickWidgets.QQuickWidget that is used by the test UI file supports only OpenGL,
        # so we need to explicitly select it via QQuickWindow.setGraphicsApi() call.
        if is_qt6:
            try:
                # This seems to be unsupported on macOS version of PySide6 at the time of writing (6.1.0)
                from {0}.QtQuick import QQuickWindow, QSGRendererInterface
                QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
            except Exception:
                pass

        # Load the UI
        ui_file = os.path.join(get_data_dir(), 'Qt_Ui_file', 'gui.ui')
        if is_pyqt:
            # Use PyQt.uic
            from {0} import uic
            window = QWidget()
            uic.loadUi(ui_file, window)
        else:
            # Use PySide.QtUiTools.QUiLoader
            from {0}.QtUiTools import QUiLoader
            loader = QUiLoader()
            window = loader.load(ui_file)
        window.show()

        # Exit Qt when the main loop becomes idle.
        QTimer.singleShot(0, app.exit)

        # Run the main loop
        if is_qt6:
            # Qt6: exec_() is deprecated in PySide6 and removed from PyQt6 in favor of exec()
            app.exec()
        else:
            app.exec_()
        """.format(QtPyLib)
    )


# Test that the ``PyQt5.Qt`` module works by importing something from it.
#
# NOTE: the ``PyQt5.Qt`` consolidating module is specific to PyQt5. It is not present in either PySide2 nor PySide6,
# and its consolidating behavior has been removed in PyQt6.
#
# The Qt Bluetooth API (which any import to ``PyQt5.Qt`` implicitly imports) is not compatible with Windows Server
# 2012 R2, the OS Appveyor runs. Specifically, running on Server 2012 causes the test to display an error in
# `a dialog box <https://github.com/mindfulness-at-the-computer/mindfulness-at-the-computer/issues/234>`_.
# The alternative of using a newer Appveyor OS `fails <https://github.com/pyinstaller/pyinstaller/pull/3563>`_.
# Therefore, skip this test on Appveyor by testing for one of its `environment variables
# <https://www.appveyor.com/docs/environment-variables/>`_.
@skipif(os.environ.get('APPVEYOR') == 'True', reason='The Appveyor OS is incompatible with PyQt.Qt.')
@requires('PyQt5')
@pytest.mark.skipif(
    is_module_satisfies('PyQt5 == 5.11.3') and is_darwin,
    reason='This version of the OS X wheel does not include QWebEngine.'
)
def test_PyQt5_Qt(pyi_builder, monkeypatch):
    _qt_dll_path_clean(monkeypatch, 'PyQt5')
    pyi_builder.test_source('from PyQt5.Qt import QLibraryInfo', **USE_WINDOWED_KWARG)


# Run the the QtWebEngine test for chosen Qt-based package flavor.
def _test_Qt_QtWebEngine(pyi_builder, monkeypatch, qt_flavor):
    _qt_dll_path_clean(monkeypatch, qt_flavor)

    if is_darwin:
        # QtWebEngine on Mac OS only works with a onedir build -- onefile builds do not work.
        # Skip the test execution for onefile builds.
        if pyi_builder._mode != 'onedir':
            pytest.skip('QtWebEngine on macOS is supported only in onedir mode.')

    source = """
        from {0}.QtWidgets import QApplication
        from {0}.QtWebEngineWidgets import QWebEngineView
        from {0}.QtCore import QUrl, QTimer

        is_qt6 = '{0}' in {{'PyQt6', 'PySide6'}}

        # Web page to display
        WEB_PAGE_HTML = '''
            <!doctype html>
            <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <title>Test web page</title>
                </head>
                <body>
                    <p>This is a test web page with internationalised characters.</p>
                    <p>HЯ⾀ÄÉÖÜ</p>
                </body>
            </html>
        '''

        app = QApplication([])

        view = QWebEngineView()
        view.setHtml(WEB_PAGE_HTML)
        view.show()
        view.page().loadFinished.connect(
            # Display the web page for one second after it loads.
            lambda ok: QTimer.singleShot(1000, app.quit))

        if is_qt6:
            # Qt6: exec_() is deprecated in PySide6 and removed from PyQt6 in favor of exec()
            app.exec()
        else:
            app.exec_()
        """.format(qt_flavor)

    pyi_builder.test_source(source, **USE_WINDOWED_KWARG)


@requires('PyQt5')
@requires('PyQtWebEngine')
def test_Qt_QtWebEngine_PyQt5(pyi_builder, monkeypatch):
    _test_Qt_QtWebEngine(pyi_builder, monkeypatch, 'PyQt5')


@requires('PySide2')
def test_Qt_QtWebEngine_PySide2(pyi_builder, monkeypatch):
    _test_Qt_QtWebEngine(pyi_builder, monkeypatch, 'PySide2')


@requires('PyQt6 >= 6.2.2')
@requires('PyQt6-WebEngine')  # NOTE: base Qt6 must be 6.2.2 or newer, QtWebEngine can be older
def test_Qt_QtWebEngine_PyQt6(pyi_builder, monkeypatch):
    _test_Qt_QtWebEngine(pyi_builder, monkeypatch, 'PyQt6')


@requires('PySide6 >= 6.2.2')
def test_Qt_QtWebEngine_PySide6(pyi_builder, monkeypatch):
    _test_Qt_QtWebEngine(pyi_builder, monkeypatch, 'PySide6')


# QtMultimedia test that also uses PySide's true_property, which triggers hidden dependency on QtMultimediaWidgets
# python module.
# See:
# https://github.com/pyinstaller/pyinstaller/pull/6496#issuecomment-1011098019
# https://github.com/qtproject/pyside-pyside-setup/blob/5.15.2/sources/shiboken2/shibokenmodule/files.dir/shibokensupport/signature/mapping.py#L577-L586
# https://github.com/qtproject/pyside-pyside-setup/blob/v6.2.2.1/sources/shiboken6/shibokenmodule/files.dir/shibokensupport/signature/mapping.py#L614-L627
@pytest.mark.parametrize('QtPyLib', [
    qt_param('PySide2'),
    qt_param('PySide6'),
])
def test_Qt_QtMultimedia_with_true_property(pyi_builder, monkeypatch, QtPyLib):
    _qt_dll_path_clean(monkeypatch, QtPyLib)
    pyi_builder.test_source(
        """
        from {0} import QtCore, QtMultimedia
        from __feature__ import true_property

        app = QtCore.QCoreApplication()
        """.format(QtPyLib), **USE_WINDOWED_KWARG
    )
