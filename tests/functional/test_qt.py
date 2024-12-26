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

import os

import pytest

from PyInstaller import isolated
from PyInstaller.compat import is_win, is_darwin, is_linux
from PyInstaller.utils.hooks import check_requirement, can_import_module
from PyInstaller.utils.hooks.qt import get_qt_library_info
from PyInstaller.utils.tests import importorskip, requires, skipif, onedir_only


def qt_param(qt_flavor, *args, **kwargs):
    """
    A Qt flavour to be used in @pytest.mark.parametrize(). Implicitly skips the test if said flavor is not installed.
    """
    p = pytest.param(qt_flavor, *args, **kwargs)
    return pytest.param(*p.values, marks=(requires(qt_flavor),) + p.marks, id=p.id)


# Parametrize test to run the same basic code on both Python Qt libraries.
_QT_PY_PACKAGES = ['PyQt5', 'PyQt6', 'PySide2', 'PySide6']
QtPyLibs = pytest.mark.parametrize('QtPyLib', [qt_param(i) for i in _QT_PY_PACKAGES])

# macOS .app bundles, produced by the ``--windowed`` flag, invoke a unique code path that sometimes causes failures in
# Qt applications. So build with ``--windowed`` option, which will build and run both POSIX build and .app bundle.
USE_WINDOWED_KWARG = dict(pyi_args=['--windowed']) if is_darwin else {}


# We need to ensure that all QtLibraryInfo structures in Qt hook utils are initialized at this point, before the actual
# tests start. This is to prevent test-order-dependent behavior and potential issues, and applies to all platforms.
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


@QtPyLibs
def test_Qt_QtWidgets(pyi_builder, QtPyLib):
    pyi_builder.test_source(
        f"""
        import sys

        from {QtPyLib}.QtWidgets import QApplication, QWidget
        from {QtPyLib}.QtCore import QTimer

        is_qt6 = '{QtPyLib}' in {{'PySide6', 'PyQt6'}}

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
        """, **USE_WINDOWED_KWARG
    )


@QtPyLibs
def test_Qt_QtQml(pyi_builder, QtPyLib):
    # Qt6 6.6.3 split Qt Quick Controls 2 styles into separate shared libraries, and both PySide6 6.6.3 and PyQt6 6.6.3
    # PyPI wheels failed to account for that. Skip this test if running with affected version.
    if QtPyLib == 'PyQt6':
        # With PyQt6, the shared libraries are missing on Windows and Linux, but not on macOS.
        if not is_darwin and check_requirement('PyQt6-Qt6 == 6.6.3'):
            pytest.skip('PyQt6-Qt6 6.6.3 is missing shared libraries required by Qt Quick Controls 2.')
    if QtPyLib == 'PySide6':
        # With PySide6, all OSes seem to be affected.
        if check_requirement('PySide6-Essentials == 6.6.3'):
            pytest.skip('PySide6-Essentials 6.6.3 is missing shared libraries required by Qt Quick Controls 2.')

    pyi_builder.test_source(
        f"""
        import sys

        from {QtPyLib}.QtGui import QGuiApplication
        from {QtPyLib}.QtQml import QQmlApplicationEngine
        from {QtPyLib}.QtCore import QTimer, QUrl

        is_qt6 = '{QtPyLib}' in {{'PyQt6', 'PySide6'}}

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
        """, **USE_WINDOWED_KWARG
    )


@QtPyLibs
def test_Qt_QtNetwork_SSL_support(pyi_builder, QtPyLib):
    # Skip the test if QtNetwork does not support SSL (e.g., due to lack of compatible OpenSSL shared library on the
    # test system). Starting with Qt 6.1, different backends provide TLS functionality, so explicitly check if
    # 'openssl' backend is available.
    @isolated.decorate
    def check_openssl_support(package):
        import sys
        import importlib

        QtCore = importlib.import_module('.QtCore', package)
        QtNetwork = importlib.import_module('.QtNetwork', package)

        # We must initialize QCoreApplication before using QtNetwork
        app = QtCore.QCoreApplication(sys.argv)  # noqa: F841

        if not QtNetwork.QSslSocket.supportsSsl():
            return False

        # For Qt >= 6.1, check if `openssl` TLS backend is available
        try:
            qt_version = QtCore.QLibraryInfo.version().segments()
        except AttributeError:
            qt_version = []  # Qt <= 5.8

        if qt_version < [6, 1]:
            return True  # TLS backends not implemented yet

        return 'openssl' in QtNetwork.QSslSocket.availableBackends()

    if not check_openssl_support(QtPyLib):
        pytest.skip('QtNetwork does not use OpenSSL.')

    pyi_builder.test_source(
        f"""
        import sys
        from {QtPyLib}.QtCore import QCoreApplication, QLibraryInfo
        from {QtPyLib}.QtNetwork import QSslSocket

        app = QCoreApplication(sys.argv)

        # Make sure SSL is supported
        assert QSslSocket.supportsSsl(), "SSL not supported!"

        # Display OpenSSL info
        print(
            f"OpenSSL build version: {{QSslSocket.sslLibraryBuildVersionNumber():X}} "
            f"({{QSslSocket.sslLibraryBuildVersionString()}})"
        )
        print(
            f"OpenSSL run-time version: {{QSslSocket.sslLibraryVersionNumber():X}} "
            f"({{QSslSocket.sslLibraryVersionString()}})"
        )

        # Obtain Qt version
        try:
            qt_version = QLibraryInfo.version().segments()
        except AttributeError:
            qt_version = []  # Qt <= 5.8

        # If Qt supports TLS backends (>= 6.1), make sure OpenSSL backend is available.
        if qt_version >= [6, 1]:
            print(f"Active TLS backend: {{QSslSocket.activeBackend()}}")
            print(f"Available TLS backends: {{QSslSocket.availableBackends()}}")
            assert 'openssl' in QSslSocket.availableBackends(), "OpenSSL TLS backend not available!"
        """, **USE_WINDOWED_KWARG
    )


@QtPyLibs
def test_Qt_QTranslate(pyi_builder, QtPyLib):
    pyi_builder.test_source(
        f"""
        import sys
        from {QtPyLib}.QtWidgets import QApplication
        from {QtPyLib}.QtCore import QTranslator, QLocale, QLibraryInfo

        # Initialize Qt default translations
        app = QApplication(sys.argv)
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
        """
    )


@QtPyLibs
def test_Qt_Ui_file(pyi_builder, data_dir, QtPyLib):
    pyi_builder.test_source(
        f"""
        import os
        import sys

        import {QtPyLib}.QtQuickWidgets  # Used instead of hiddenimports

        from {QtPyLib}.QtWidgets import QApplication, QWidget
        from {QtPyLib}.QtCore import QTimer

        is_qt6 = '{QtPyLib}' in {{'PyQt6', 'PySide6'}}
        is_pyqt = '{QtPyLib}' in {{'PyQt5', 'PyQt6'}}

        app = QApplication(sys.argv)

        # In Qt6, QtQuick supports multiple render APIs and automatically selects one.
        # However, QtQuickWidgets.QQuickWidget that is used by the test UI file supports only OpenGL,
        # so we need to explicitly select it via QQuickWindow.setGraphicsApi() call.
        if is_qt6:
            try:
                # This seems to be unsupported on macOS version of PySide6 at the time of writing (6.1.0)
                from {QtPyLib}.QtQuick import QQuickWindow, QSGRendererInterface
                QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
            except Exception:
                pass

        # Load the UI
        ui_file = os.path.join(os.path.dirname(__file__), 'gui.ui')
        if is_pyqt:
            # Use PyQt.uic
            from {QtPyLib} import uic
            window = QWidget()
            uic.loadUi(ui_file, window)
        else:
            # Use PySide.QtUiTools.QUiLoader
            from {QtPyLib}.QtUiTools import QUiLoader
            loader = QUiLoader()
            window = loader.load(ui_file)
        window.show()

        # Exit Qt when the main loop becomes idle.
        QTimer.singleShot(0, app.exit)

        # Run the main loop
        if is_qt6:
            # Qt6: exec_() is deprecated in PySide6 and removed from PyQt6 in favor of exec()
            res = app.exec()
        else:
            res = app.exec_()
        sys.exit(res)
        """,
        # Collect the .ui file into top-level application directory.
        pyi_args=['--add-data', f"{data_dir / 'gui.ui'}:."],
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
    check_requirement('PyQt5 == 5.11.3') and is_darwin,
    reason='This version of the macOS wheel does not include QWebEngine.'
)
def test_PyQt5_Qt(pyi_builder):
    pyi_builder.test_source('from PyQt5.Qt import QLibraryInfo', **USE_WINDOWED_KWARG)


# QtWebEngine tests


# On linux systems with glibc >= 2.34, QtWebEngine helper process crashes with SIGSEGV due to use of `clone3` syscall,
# which is incompatible with chromium sandbox (see QTBUG-96214). The issue was fixed in Qt5 5.15.7, however even the
# latest PyPI wheels of PySide2 (5.15.2.1) and PyQt5/PyQtWebEngine (5.15.6) still seem to ship Qt5 5.15.2 (which was
# probably last publicly available linux build from the Qt itself). If we encounter incompatible combination of
# glibc and Qt5 (for example, using PyPI wheels under Ubuntu 22.04), we disable the sandbox, which allows us to perform
# basic functionality test.
def _disable_qtwebengine_sandbox(qt_flavor):
    if is_linux:
        import platform

        # Check glibc version
        libc_name, libc_version = platform.libc_ver()
        if libc_name != 'glibc':
            return False
        try:
            libc_version = [int(v) for v in libc_version.split('.')]
        except Exception:
            return False
        if libc_version < [2, 34]:
            return False

        # Check Qt version
        qt_info = get_qt_library_info(qt_flavor)
        if qt_info.version and qt_info.version >= [5, 15, 7]:
            return False

        # Incompatible glibc and Qt5 version
        return True

    return False


# Run the the QtWebEngineWidgets test for chosen Qt-based package flavor.
def _test_Qt_QtWebEngineWidgets(pyi_builder, qt_flavor):
    disable_sandbox = _disable_qtwebengine_sandbox(qt_flavor)
    pyi_builder.test_source(
        f"""
        import sys

        # Disable QtWebEngine/chromium sanbox, if necessary
        if {disable_sandbox}:
            import os
            os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'

        from {qt_flavor}.QtWidgets import QApplication
        from {qt_flavor}.QtWebEngineWidgets import QWebEngineView
        from {qt_flavor}.QtCore import QTimer

        is_qt6 = '{qt_flavor}' in {{'PyQt6', 'PySide6'}}

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

        app = QApplication(sys.argv)

        class JSResultTester:

            CODE = "1+1"
            EXPECTED = 2

            def __init__(self):
                self.result = None

            def setup(self, view):
                # Need to explicitly pass 0 as world id due to
                # https://bugreports.qt.io/browse/PYSIDE-643
                view.page().runJavaScript(self.CODE, 0, self.store)

                view.page().loadFinished.connect(
                    # Display the web page for one second after it loads.
                    lambda ok: QTimer.singleShot(1000, self.verify_and_quit))

            def store(self, res):
                self.result = res

            def verify_and_quit(self):
                # Make sure the renderer process is alive.
                if self.result != self.EXPECTED:
                    raise ValueError(
                        f"JS result is {{self.result!r}} but expected {{self.EXPECTED!r}}. "
                        "Is the QtWebEngine renderer process running properly?")
                app.quit()

        view = QWebEngineView()
        view.setHtml(WEB_PAGE_HTML)
        view.show()

        js_result_tester = JSResultTester()
        js_result_tester.setup(view)

        if is_qt6:
            # Qt6: exec_() is deprecated in PySide6 and removed from PyQt6 in favor of exec()
            res = app.exec()
        else:
            res = app.exec_()
        sys.exit(res)
        """, **USE_WINDOWED_KWARG
    )


# Run the the QtWebEngineQuick test for chosen Qt-based package flavor.
def _test_Qt_QtWebEngineQuick(pyi_builder, qt_flavor):
    disable_sandbox = _disable_qtwebengine_sandbox(qt_flavor)
    pyi_builder.test_source(
        f"""
        import sys

        # Disable QtWebEngine/chromium sanbox, if necessary
        if {disable_sandbox}:
            import os
            os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'

        from {qt_flavor}.QtGui import QGuiApplication
        from {qt_flavor}.QtQml import QQmlApplicationEngine

        is_qt6 = '{qt_flavor}' in {{'PyQt6', 'PySide6'}}

        if is_qt6:
            from {qt_flavor}.QtWebEngineQuick import QtWebEngineQuick
        else:
            from {qt_flavor}.QtWebEngine import QtWebEngine as QtWebEngineQuick
        QtWebEngineQuick.initialize()

        app = QGuiApplication(sys.argv)
        engine = QQmlApplicationEngine()
        engine.loadData(b'''
            import QtQuick 2.0
            import QtQuick.Window 2.0
            import QtWebEngine 1.0

            Window {{
                visible: true
                WebEngineView {{
                    id: view
                    anchors.fill: parent
                    Component.onCompleted: loadHtml('
                        <!doctype html>
                        <html lang="en">
                            <head>
                                <meta charset="utf-8">
                                <title>Test web page</title>
                            </head>
                            <body>
                                <p>This is a test web page.</p>
                            </body>
                        </html>
                    ')
                }}
                Connections {{
                    target: view
                    function onLoadingChanged(loadRequest) {{
                        if (loadRequest.status !== WebEngineView.LoadStartedStatus) {{
                            Qt.quit()
                        }}
                    }}
                }}
            }}
        ''')

        if not engine.rootObjects():
            sys.exit(-1)

        if is_qt6:
            # Qt6: exec_() is deprecated in PySide6 and removed from PyQt6 in favor of exec()
            res = app.exec()
        else:
            res = app.exec_()
        del engine
        sys.exit(res)
        """, **USE_WINDOWED_KWARG
    )


@requires('PyQt5')
@requires('PyQtWebEngine')
def test_Qt_QtWebEngineWidgets_PyQt5(pyi_builder):
    _test_Qt_QtWebEngineWidgets(pyi_builder, 'PyQt5')


@requires('PyQt5')
@requires('PyQtWebEngine')
def test_Qt_QtWebEngineQuick_PyQt5(pyi_builder):
    _test_Qt_QtWebEngineQuick(pyi_builder, 'PyQt5')


@requires('PySide2')
def test_Qt_QtWebEngineWidgets_PySide2(pyi_builder):
    _test_Qt_QtWebEngineWidgets(pyi_builder, 'PySide2')


@requires('PySide2')
def test_Qt_QtWebEngineQuick_PySide2(pyi_builder):
    _test_Qt_QtWebEngineQuick(pyi_builder, 'PySide2')


@requires('PyQt6 >= 6.2.2')
@requires('PyQt6-WebEngine')  # NOTE: base Qt6 must be 6.2.2 or newer, QtWebEngine can be older
def test_Qt_QtWebEngineWidgets_PyQt6(pyi_builder):
    _test_Qt_QtWebEngineWidgets(pyi_builder, 'PyQt6')


@requires('PyQt6 >= 6.2.2')
@requires('PyQt6-WebEngine')  # NOTE: base Qt6 must be 6.2.2 or newer, QtWebEngine can be older
@pytest.mark.skipif(
    check_requirement('PyQt6-Qt6 == 6.6.0'),
    reason='PyQt6 6.6.0 PyPI wheels are missing Qt6WebChannelQuick shared library.'
)
@pytest.mark.skipif(
    check_requirement('PyQt6-Qt6 == 6.6.3') and is_win,
    reason='PyQt6 6.6.3 PyPI wheels for Windows are missing Qt6WebChannelQuick shared library.'
)
def test_Qt_QtWebEngineQuick_PyQt6(pyi_builder):
    _test_Qt_QtWebEngineQuick(pyi_builder, 'PyQt6')


@requires('PySide6 >= 6.2.2')
@pytest.mark.skipif(
    check_requirement('PySide6 == 6.5.0') and is_win,
    reason='PySide6 6.5.0 PyPI wheels for Windows are missing opengl32sw.dll.'
)
def test_Qt_QtWebEngineWidgets_PySide6(pyi_builder):
    _test_Qt_QtWebEngineWidgets(pyi_builder, 'PySide6')


@requires('PySide6 >= 6.2.2')
@pytest.mark.skipif(
    check_requirement('PySide6 == 6.5.0') and is_win,
    reason='PySide6 6.5.0 PyPI wheels for Windows are missing opengl32sw.dll.'
)
def test_Qt_QtWebEngineQuick_PySide6(pyi_builder):
    _test_Qt_QtWebEngineQuick(pyi_builder, 'PySide6')


# QtMultimedia test that triggers error when the module's plugins are missing (#7352).
@QtPyLibs
def test_Qt_QtMultimedia_player_init(pyi_builder, QtPyLib):
    # QtMultimedia in PyQt6-Qt6 6.7.1 does not seem to be compatible with PyQt6 6.7.0 (the PyQt6-Qt6 6.7.1 update was
    # pushed on Jun 2 2024 without PyQt6 itself being updated).
    if QtPyLib == 'PyQt6':
        if check_requirement('PyQt6-Qt6 == 6.7.1') and check_requirement('PyQt6 == 6.7.0'):
            pytest.skip('QtMultimedia is broken under PyQt6 6.7.0 and PyQt6-Qt6 6.7.1.')

    pyi_builder.test_source(
        f"""
        import sys

        from {QtPyLib} import QtCore, QtMultimedia

        app = QtCore.QCoreApplication(sys.argv)
        player = QtMultimedia.QMediaPlayer(app)
        """, **USE_WINDOWED_KWARG
    )


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
def test_Qt_QtMultimedia_with_true_property(pyi_builder, QtPyLib):
    pyi_builder.test_source(
        f"""
        import sys
        from {QtPyLib} import QtCore, QtMultimedia
        from __feature__ import true_property

        app = QtCore.QCoreApplication(sys.argv)
        """, **USE_WINDOWED_KWARG
    )


# In PySide6 >= 6.4.0, we need to collect `PySide6.support.deprecated` module for logical operators between Qt key and
# key modifier enums to work. See #7249.
@requires('PySide6')
def test_Qt_PySide6_key_enums(pyi_builder):
    pyi_builder.test_source(
        """
        from PySide6 import QtCore
        key = QtCore.Qt.AltModifier | QtCore.Qt.Key_D
        """
    )


# Basic import tests for all Qt-bindings-provided modules. Each module should be importable on its own, which requires a
# corresponding hook that performs recursive analysis of the module in order to collect all of its dependencies.
#
# Due to the sheer amount of tests, they are ran only in onedir mode.


# Helper that lists all Qt* modules from a Qt-based package. Ran isolated to prevent import affecting the main process.
@isolated.decorate
def _list_all_qt_submodules(package_name):
    import importlib
    import pkgutil

    try:
        package = importlib.import_module(package_name)
    except Exception:
        return []

    return sorted([
        module_info.name for module_info in pkgutil.iter_modules(package.__path__) if module_info.name.startswith("Qt")
    ])


def _test_qt_bindings_import(bindings, module, pyi_builder_onedir):
    # Check if particular module is importable. This guards against errors if a module is unavailable in particular
    # version of the bindings, or if it is provided by an extra package that is not installed.
    modname = bindings + "." + module
    if not can_import_module(modname):
        pytest.skip(f"Module '{modname}' cannot be imported.")
    # Basic import test
    # The import of the tested module is preceeded by import of the QtCore. This seems to prevent segfaults on macOS
    # with certain modules in the frozen test (QtSensors in PySide2 and PyQt5, QtWebEngine* in PySide6, etc.). The
    # segfaults occur when trying to resolve bundle identifier, which may be related to PyInstaller failing to
    # preserve the .framework bundle structure for Qt shared libraries (and importing QtCore somehow works around
    # that). Since QtCore is practically a dependency of all other Qt modules, its import does not affect the results
    # of the test much.
    pyi_builder_onedir.test_source(f"""
        import {bindings}.QtCore
        import {modname}
        """)


@importorskip('PySide2')
@pytest.mark.parametrize('module', _list_all_qt_submodules('PySide2'))
@onedir_only
def test_qt_module_import_PySide2(module, pyi_builder):
    _test_qt_bindings_import("PySide2", module, pyi_builder)


@importorskip('PySide6')
@pytest.mark.parametrize('module', _list_all_qt_submodules('PySide6'))
@onedir_only
def test_qt_module_import_PySide6(module, pyi_builder):
    _test_qt_bindings_import("PySide6", module, pyi_builder)


@importorskip('PyQt5')
@pytest.mark.parametrize('module', _list_all_qt_submodules('PyQt5'))
@onedir_only
def test_qt_module_import_PyQt5(module, pyi_builder):
    _test_qt_bindings_import("PyQt5", module, pyi_builder)


@importorskip('PyQt6')
@pytest.mark.parametrize('module', _list_all_qt_submodules('PyQt6'))
@onedir_only
def test_qt_module_import_PyQt6(module, pyi_builder):
    _test_qt_bindings_import("PyQt6", module, pyi_builder)
