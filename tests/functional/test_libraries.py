# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import pytest
import os

# Local imports
# -------------
import sys

from PyInstaller.compat import is_win, is_py3, is_py36, is_darwin
from PyInstaller.utils.hooks import get_module_attribute, is_module_satisfies
from PyInstaller.utils.tests import importorskip, xfail, skipif

# :todo: find a way to get this from `conftest` or such
# Directory with testing modules used in some tests.
_MODULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')

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


@importorskip('cherrypy')
def test_cherrypy(pyi_builder):
    # import wsgiserver3 on Python 3, or else wsgiserver2 on Python 2.
    pyi_builder.test_source(
        """
        import cherrypy.wsgiserver.wsgiserver%s
        """ % sys.version_info[0])


@xfail(is_darwin, reason='Issue #1895.')
@importorskip('enchant')
def test_enchant(pyi_builder):
    pyi_builder.test_script('pyi_lib_enchant.py')


@importorskip('gevent')
def test_gevent(pyi_builder):
    pyi_builder.test_source(
        """
        import gevent
        gevent.spawn(lambda: x)
        """)


@xfail(is_py36, reason='Fails on python 3.6')
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

    from PyInstaller.building.build_main import Analysis
    class MyAnalysis(Analysis):
        def __init__(self, *args, **kwargs):
            kwargs['datas'] = datas
            # Setting back is required to make `super()` within
            # Analysis access the correct class. Do not use
            # `monkeypatch.undo()` as this will undo *all*
            # monkeypathes.
            monkeypatch.setattr('PyInstaller.building.build_main.Analysis',
                                Analysis)
            super(MyAnalysis, self).__init__(*args, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', MyAnalysis)

    # Include some data files for testing pkg_resources module.
    # :fixme: When PyInstaller supports setting datas via the
    # command-line, us this here instead of monkeypatching Analysis.
    datas = [(os.path.join(_MODULES_DIR, 'pkg3', 'sample-data.txt'), 'pkg3')]
    pyi_builder.test_script('pkg_resource_res_string.py')


def test_pkgutil_get_data(pyi_builder, monkeypatch):

    from PyInstaller.building.build_main import Analysis
    class MyAnalysis(Analysis):
        def __init__(self, *args, **kwargs):
            kwargs['datas'] = datas
            # Setting back is required to make `super()` within
            # Analysis access the correct class. Do not use
            # `monkeypatch.undo()` as this will undo *all*
            # monkeypathes.
            monkeypatch.setattr('PyInstaller.building.build_main.Analysis',
                                Analysis)
            super(MyAnalysis, self).__init__(*args, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', MyAnalysis)

    # Include some data files for testing pkg_resources module.
    # :fixme: When PyInstaller supports setting datas via the
    # command-line, us this here instead of monkeypatching Analysis.
    datas = [(os.path.join(_MODULES_DIR, 'pkg3', 'sample-data.txt'), 'pkg3')]
    pyi_builder.test_script('pkgutil_get_data.py')


@xfail(reason='Our import mechanism returns the wrong loader-class for __main__.')
def test_pkgutil_get_data__main__(pyi_builder, monkeypatch):

    from PyInstaller.building.build_main import Analysis
    class MyAnalysis(Analysis):
        def __init__(self, *args, **kwargs):
            kwargs['datas'] = datas
            # Setting back is required to make `super()` within
            # Analysis access the correct class. Do not use
            # `monkeypatch.undo()` as this will undo *all*
            # monkeypathes.
            monkeypatch.setattr('PyInstaller.building.build_main.Analysis',
                                Analysis)
            super(MyAnalysis, self).__init__(*args, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', MyAnalysis)

    # Include some data files for testing pkg_resources module.
    # :fixme: When PyInstaller supports setting datas via the
    # command-line, us this here instead of monkeypatching Analysis.
    datas = [(os.path.join(_MODULES_DIR, 'pkg3', 'sample-data.txt'), 'pkg3')]
    pyi_builder.test_script('pkgutil_get_data__main__.py')



@importorskip('sphinx')
def test_sphinx(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_sphinx.py')


@xfail(is_py36, reason='Fails on python 3.6')
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


@pytest.mark.skipif(is_module_satisfies('Qt >= 5.6', get_module_attribute('PyQt5.QtCore', 'QT_VERSION_STR')),
                    reason='QtWebKit is depreciated in Qt 5.6+')
@importorskip('PyQt5')
def test_PyQt5_uic(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_PyQt5-uic.py')


@importorskip('zope.interface')
def test_zope_interface(pyi_builder):
    # Tests that modules without __init__.py file are bundled properly.
    pyi_builder.test_source(
        """
        # Package 'zope' does not contain __init__.py file.
        # Just importing 'zope.interface' is sufficient.
        import zope.interface
        """)


@xfail(is_darwin, reason='Issue #1895.')
@importorskip('idlelib')
def test_idlelib(pyi_builder):
    pyi_builder.test_source(
        """
        # This file depends on loading some icons, located based on __file__.
        import idlelib.TreeWidget
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
            AES.new("\\0" * BLOCK_SIZE).encrypt("\\0" * BLOCK_SIZE)))
        """)

@importorskip('requests')
def test_requests(tmpdir, pyi_builder, data_dir, monkeypatch):
    # Note that including the data_dir fixture copies files needed by this test.

    from PyInstaller.building.build_main import Analysis
    class MyAnalysis(Analysis):
        def __init__(self, *args, **kwargs):
            kwargs['datas'] = datas
            # Setting back is required to make `super()` within
            # Analysis access the correct class. Do not use
            # `monkeypatch.undo()` as this will undo *all*
            # monkeypathes.
            monkeypatch.setattr('PyInstaller.building.build_main.Analysis',
                                Analysis)
            super(MyAnalysis, self).__init__(*args, **kwargs)

    monkeypatch.setattr('PyInstaller.building.build_main.Analysis', MyAnalysis)

    # Include the data files.
    # :fixme: When PyInstaller supports setting datas via the
    # command-line, us this here instead of monkeypatching Analysis.
    datas = [(str(data_dir.join('*')), '.')]
    pyi_builder.test_script('pyi_lib_requests.py')


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
@pytest.mark.skipif(is_win, reason='Python 3 syntax error on Windows')
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
@pytest.mark.xfail(reason='TODO - known to fail')
def test_pyexcelerate(pyi_builder):
    pyi_builder.test_source(
        """
        # Requires PyExcelerate 0.6.1 or higher
        # Tested on Windows 7 x64 SP1 with CPython 2.7.6
        import pyexcelerate
        """)


@importorskip('usb')
def test_usb(pyi_builder):
    # See if the usb package is supported on this platform.
    try:
        import usb
        # This will verify that the backend is present; if not, it will
        # skip this test.
        usb.core.find(find_all = True)
    except (ImportError, ValueError):
        pytest.skip('USB backnd not found.')

    pyi_builder.test_source(
        """
        import usb.core
        # Detect usb devices.
        devices = usb.core.find(find_all = True)
        if not devices:
            raise SystemExit('No USB device found.')
        """)


@importorskip('PIL')
@pytest.mark.xfail(reason="Fails with Pillow 3.0.0")
def test_pil_img_conversion(pyi_builder_spec):
    pyi_builder_spec.test_spec('pyi_lib_PIL_img_conversion.spec')


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
    # Tests that C extension 'pandas.lib' is properly bundled. Issue #1580.
    pyi_builder.test_source(
        """
        from pandas.lib import is_float
        assert is_float(1) == 0
        """)
