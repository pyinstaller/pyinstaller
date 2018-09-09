# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import py
import pytest
import os

# Local imports
# -------------
from PyInstaller.compat import is_win, is_py3, is_py35, is_py36, is_py37, \
    is_darwin, is_linux, is_64bits
from PyInstaller.utils.hooks import get_module_attribute, is_module_satisfies
from PyInstaller.utils.tests import importorskip, xfail, skipif

# :todo: find a way to get this from `conftest` or such
# Directory with testing modules used in some tests.
_MODULES_DIR = py.path.local(os.path.abspath(__file__)).dirpath('modules')
_DATA_DIR = py.path.local(os.path.abspath(__file__)).dirpath('data')

@importorskip('boto')
@pytest.mark.skipif(is_py3, reason='boto does not fully support Python 3')
def test_boto(pyi_builder):
    pyi_builder.test_script('pyi_lib_boto.py')


@xfail(reason='Issue #1844.')
@importorskip('boto3')
def test_boto3(pyi_builder):
    pyi_builder.test_source(
        """
        import boto3
        session = boto3.Session(region_name='us-west-2')

        # verify all clients
        for service in session.get_available_services():
            session.client(service)

        # verify all resources
        for resource in session.get_available_resources():
            session.resource(resource)
        """)


@xfail(reason='Issue #1844.')
@importorskip('botocore')
def test_botocore(pyi_builder):
    pyi_builder.test_source(
        """
        import botocore
        from botocore.session import Session
        session = Session()
        # verify all services
        for service in session.get_available_services():
            session.create_client(service, region_name='us-west-2')
        """)


@xfail(is_darwin, reason='Issue #1895.')
@importorskip('enchant')
def test_enchant(pyi_builder):
    pyi_builder.test_script('pyi_lib_enchant.py')


@skipif(is_py3, reason="Only tests Python 2.7 feature")
def test_future(pyi_builder):
    pyi_builder.test_script('pyi_future.py')


@skipif(is_py3, reason="Only tests Python 2.7 feature")
def test_future_queue(pyi_builder):
    pyi_builder.test_source(
        """
        import queue
        queue.Queue()
        """
    )


@importorskip('gevent')
def test_gevent(pyi_builder):
    pyi_builder.test_source(
        """
        import gevent
        gevent.spawn(lambda: x)
        """)


@importorskip('gevent')
def test_gevent_monkey(pyi_builder):
    pyi_builder.test_source(
        """
        from gevent.monkey import patch_all
        patch_all()
        """)


@xfail(is_darwin, reason='Issue #1895.')
def test_tkinter(pyi_builder):
    pyi_builder.test_script('pyi_lib_tkinter.py')


@xfail(is_darwin, reason='Issue #1895.')
@importorskip('FixTk')
def test_tkinter_FixTk(pyi_builder):
    # check if Tkinter includes FixTk
    # TODO: Python 3 contains module 'tkinter._fix' - does it need any special test or handling?
    # TODO: How does the following code check if FixTk is included?
    pyi_builder.test_source("""
    try:
        # In Python 2 the module name is 'Tkinter'
        import Tkinter
    except ImportError:
        import tkinter
    """)

@importorskip('zmq')
def test_zmq(pyi_builder):
    pyi_builder.test_source(
        """
        import zmq
        print(zmq.__version__)
        print(zmq.zmq_version())
        # This is a problematic module and might cause some issues.
        import zmq.utils.strtypes
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


@xfail(reason='Our import mechanism returns the wrong loader-class for __main__.')
def test_pkgutil_get_data__main__(pyi_builder, monkeypatch):
    # Include some data files for testing pkg_resources module.
    datas = os.pathsep.join((str(_MODULES_DIR.join('pkg3', 'sample-data.txt')),
                             'pkg3'))
    pyi_builder.test_script('pkgutil_get_data__main__.py',
                            pyi_args=['--add-data', datas])


@importorskip('sphinx')
def test_sphinx(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_sphinx.py')


@importorskip('pylint')
def test_pylint(pyi_builder):
    pyi_builder.test_source(
        """
        # The following more obvious test doesn't work::
        #
        #   import pylint
        #   pylint.run_pylint()
        #
        # because pylint will exit with 32, since a valid command
        # line wasn't given. Instead, provide a valid command line below.

        from pylint.lint import Run
        Run(['-h'])
        """)


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

@importorskip('markdown')
def test_markdown(pyi_builder):
    # Markdown uses __import__ed extensions. Make sure these work by
    # trying to use the 'toc' extension..
    pyi_builder.test_source(
        """
        import markdown
        print(markdown.markdown('testing',  ['toc']))
        """)


@importorskip('PyQt4')
def test_PyQt4_QtWebKit(pyi_builder):
    pyi_builder.test_source(
        """
        from PyQt4.QtGui import QApplication
        from PyQt4.QtWebKit import QWebView
        from PyQt4.QtCore import QTimer

        app = QApplication([])
        view = QWebView()
        view.show()
        # Exit Qt when the main loop becomes idle.
        QTimer.singleShot(0, app.exit)
        # Run the main loop, displaying the WebKit widget.
        app.exec_()
        """)


@importorskip('PyQt4')
def test_PyQt4_uic(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_PyQt4-uic.py')


@pytest.mark.skipif(is_module_satisfies('Qt >= 5.6', get_module_attribute('PyQt5.QtCore', 'QT_VERSION_STR')),
                    reason='QtWebKit is depreciated in Qt 5.6+')
@importorskip('PyQt5')
def test_PyQt5_QtWebKit(pyi_builder):
    pyi_builder.test_script('pyi_lib_PyQt5-QtWebKit.py')


PYQT5_NEED_OPENGL = pytest.mark.skipif(is_module_satisfies('PyQt5 <= 5.10.1'),
    reason='PyQt5 v5.10.1 and older does not package ``opengl32sw.dll``, the '
    'OpenGL software renderer, which this test requires.')


@PYQT5_NEED_OPENGL
@importorskip('PyQt5')
def test_PyQt5_uic(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_PyQt5-uic.py')


@xfail(is_darwin, reason='Please help debug this. See issue #3233.')
@pytest.mark.skipif(is_win and not is_64bits, reason="Qt 5.11+ for Windows "
    "only provides pre-compiled Qt WebEngine binaries for 64-bit processors.")
@importorskip('PyQt5')
def test_PyQt5_QWebEngine(pyi_builder, data_dir):
    pyi_builder.test_source(
        """
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtCore import QUrl, QTimer
        app = QApplication([])
        view = QWebEngineView()
        # Use a raw string to avoid accidental special characters in Windows filenames:
        # ``c:\temp`` is `c<tab>emp`!
        view.load(QUrl.fromLocalFile(r'{}'))
        view.show()
        view.page().loadFinished.connect(
            # Display the web page for two seconds after it loads.
            lambda ok: QTimer.singleShot(2000, app.quit))
        app.exec_()
        """.format(data_dir.join('test_web_page.html').strpath))


@PYQT5_NEED_OPENGL
@importorskip('PyQt5')
def test_PyQt5_QtQml(pyi_builder):
    pyi_builder.test_source(
        """
        import sys

        from PyQt5.QtGui import QGuiApplication
        from PyQt5.QtQml import QQmlApplicationEngine
        from PyQt5.QtCore import QTimer, QUrl

        # Select a style via the `command line <https://doc.qt.io/qt-5/qtquickcontrols2-styles.html#command-line-argument>`_,
        # since currently PyQt5 doesn't `support https://riverbankcomputing.com/pipermail/pyqt/2018-March/040180.html>`_
        # ``QQuickStyle``. Using this style with the QML below helps to verify
        # that all QML files are packaged; see https://github.com/pyinstaller/pyinstaller/issues/3711.
        app = QGuiApplication(sys.argv + ['-style', 'imagine'])
        engine = QQmlApplicationEngine()
        engine.loadData(b'''
            import QtQuick 2.11
            import QtQuick.Controls 2.4

            ApplicationWindow {
                visible: true
                ProgressBar {value: 0.6}
            }
            ''', QUrl())

        if not engine.rootObjects():
            sys.exit(-1)

        # Exit Qt when the main loop becomes idle.
        QTimer.singleShot(0, app.exit)

        res = app.exec_()
        del engine
        sys.exit(res)
        """)


@importorskip('PyQt5')
def test_PyQt5_SSL_support(pyi_builder):
    pyi_builder.test_source(
        """
        from PyQt5.QtNetwork import QSslSocket
        assert QSslSocket.supportsSsl()
        """)


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
def test_PyQt5_Qt(pyi_builder):
    pyi_builder.test_source('from PyQt5.Qt import QLibraryInfo')


@xfail(is_linux and is_py35, reason="Fails on linux >3.5")
@xfail(is_darwin, reason="Fails on OSX")
@xfail(is_win and is_py35 and not is_py36, reason="Fails on win == 3.6")
@importorskip('PySide2')
def test_PySide2_QWebEngine(pyi_builder):
    pyi_builder.test_source(
        """
        from PySide2.QtWidgets import QApplication
        from PySide2.QtWebEngineWidgets import QWebEngineView
        from PySide2.QtCore import QUrl
        app = QApplication( [] )
        view = QWebEngineView()
        view.load( QUrl( "http://www.pyinstaller.org" ) )
        view.show()
        view.page().loadFinished.connect(lambda ok: app.quit())
        app.exec_()
        """)


@importorskip('PySide2')
def test_PySide2_QtQuick(pyi_builder):
    pyi_builder.test_source(
        """
        import sys

        # Not used. Only here to trigger the hook
        import PySide2.QtQuick

        from PySide2.QtGui import QGuiApplication
        from PySide2.QtQml import QQmlApplicationEngine
        from PySide2.QtCore import QTimer, QUrl

        app = QGuiApplication([])
        engine = QQmlApplicationEngine()
        engine.loadData(b'''
            import QtQuick 2.0
            import QtQuick.Controls 2.0

            ApplicationWindow {
                visible: true
                color: "green"
            }
            ''', QUrl())

        if not engine.rootObjects():
            sys.exit(-1)

        # Exit Qt when the main loop becomes idle.
        QTimer.singleShot(0, app.exit)

        sys.exit(app.exec_())
        """)


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


@importorskip('lxml')
def test_lxml_isoschematron(pyi_builder):
    pyi_builder.test_source(
        """
        # The import of this module triggers the loading of some
        # required XML files.
        from lxml import isoschematron
        """)


@importorskip('numpy')
def test_numpy(pyi_builder):
    pyi_builder.test_source(
        """
        from __future__ import print_function
        import numpy
        from numpy.core.numeric import dot
        print('dot(3, 4):', dot(3, 4))
        """)


@importorskip('openpyxl')
def test_openpyxl(pyi_builder):
    pyi_builder.test_source(
        """
        # Test the hook to openpyxl
        from openpyxl import __version__
        """)


@importorskip('pyodbc')
def test_pyodbc(pyi_builder):
    pyi_builder.test_source(
        """
        # pyodbc is a binary Python module. On Windows when installed with easy_install
        # it is installed as zipped Python egg. This binary module is extracted
        # to PYTHON_EGG_CACHE directory. PyInstaller should find the binary there and
        # include it with frozen executable.
        import pyodbc
        """)


@importorskip('pytz')
def test_pytz(pyi_builder):
    pyi_builder.test_source(
        """
        import pytz
        pytz.timezone('US/Eastern')
        """)


@importorskip('pyttsx')
def test_pyttsx(pyi_builder):
    pyi_builder.test_source(
        """
        # Basic code example from pyttsx tutorial.
        # http://packages.python.org/pyttsx/engine.html#examples
        import pyttsx
        engine = pyttsx.init()
        engine.say('Sally sells seashells by the seashore.')
        engine.say('The quick brown fox jumped over the lazy dog.')
        engine.runAndWait()
        """)


@importorskip('pycparser')
def test_pycparser(pyi_builder):
    pyi_builder.test_script('pyi_lib_pycparser.py')


@importorskip('Crypto')
def test_pycrypto(pyi_builder):
    pyi_builder.test_source(
        """
        from __future__ import print_function
        import binascii
        from Crypto.Cipher import AES
        BLOCK_SIZE = 16
        print('AES null encryption, block size', BLOCK_SIZE)
        # Just for testing functionality after all
        print('HEX', binascii.hexlify(
            AES.new(b"\\0" * BLOCK_SIZE, AES.MODE_ECB).encrypt(b"\\0" * BLOCK_SIZE)))
        """)


@importorskip('Cryptodome')
def test_cryptodome(pyi_builder):
    pyi_builder.test_source(
        """
        from Cryptodome import Cipher
        print('Cryptodome Cipher Module:', Cipher)
        """)


@skipif(is_win and is_py37, reason='The call to ssl.wrap_socket produces '
        '"ssl.SSLError: [SSL: EE_KEY_TOO_SMALL] ee key too small '
        '(_ssl.c:3717)" on Windows Python 3.7.')
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
    try:
        # In Python 2 the module name is 'Tkinter'
        import Tkinter
    except ImportError:
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

@importorskip('PIL.ImageQt')
@importorskip('PyQt4')
def test_pil_PyQt4(pyi_builder):
    # hook-PIL is excluding PyQt4, but is must still be included
    # since it is imported elsewhere. Also see issue #1584.
    pyi_builder.test_source("""
    import PyQt4
    import PIL
    import PIL.ImageQt
    """)


@importorskip('PIL')
def test_pil_plugins(pyi_builder):
    pyi_builder.test_source(
        """
        # Verify packaging of PIL.Image. Specifically, the hidden import of FixTk
        # importing tkinter is causing some problems.
        from PIL.Image import fromstring
        print(fromstring)

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

@importorskip('h5py')
def test_h5py(pyi_builder):
    pyi_builder.test_source("""
        import h5py
        """)


@importorskip('unidecode')
def test_unidecode(pyi_builder):
    pyi_builder.test_source("""
        from unidecode import unidecode

        # Unidecode should not skip non-ASCII chars if mappings for them exist.
        assert unidecode(u"kožušček") == "kozuscek"
        """)


@importorskip('pinyin')
def test_pinyin(pyi_builder):
    pyi_builder.test_source("""
        import pinyin
        """)


@importorskip('uvloop')
@skipif(is_win or not is_py35, reason='Windows, or py < 3.5 not supported')
def test_uvloop(pyi_builder):
    pyi_builder.test_source("import uvloop")


@importorskip('web3')
def test_web3(pyi_builder):
    pyi_builder.test_source("import web3")


@importorskip('phonenumbers')
def test_phonenumbers(pyi_builder):
    pyi_builder.test_source("""
        import phonenumbers

        number = '+17034820623'
        parsed_number = phonenumbers.parse(number)

        assert(parsed_number.country_code == 1)
        assert(parsed_number.national_number == 7034820623)
        """)
