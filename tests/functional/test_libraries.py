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

# Local imports
# -------------
from PyInstaller.compat import is_win, is_py3
from PyInstaller.utils.tests import importorskip


@importorskip('boto')
@pytest.mark.skipif(is_py3, reason='boto does not fully support Python 3')
def test_boto(pyi_builder):
    pyi_builder.test_script('pyi_lib_boto.py')


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


@importorskip('gevent')
def test_gevent_monkey(pyi_builder):
    pyi_builder.test_source(
        """
        from gevent.monkey import patch_all
        patch_all()
        """)


def test_tkinter(pyi_builder):
    pyi_builder.test_script('pyi_lib_tkinter.py')

@importorskip('FixTk')
def test_tkinter_FixTk(pyi_builder):
    # check if Tkinter includes FixTk
    # TODO: FixTk doesn't exist in Python 3.4. Check when it was removed.
    pyi_builder.test_source("""
    try:
        # In Python 2 the module name is 'Tkinter'
        import Tkinter
    except ImportError:
        import tkinter
    """)

@importorskip('zmq')
def test_zmq(pyi_builder):
    pyi_builder.test_script('pyi_lib_zmq.py')


@importorskip('sphinx')
def test_sphinx(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_sphinx.py')

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
def test_PyQt4_uic(tmpdir, pyi_builder, data_dir):
    # Note that including the data_dir fixture copies files needed by this test.
    pyi_builder.test_script('pyi_lib_PyQt4-uic.py')

@importorskip('PyQt5')
def test_PyQt5_QtWebKit(pyi_builder):
    pyi_builder.test_script('pyi_lib_PyQt5-QtWebKit.py')

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


@importorskip('idlelib')
def test_idlelib(pyi_builder):
    pyi_builder.test_source(
        """
        # This file depends on loading some icons, located based on __file__.
        import idlelib.TreeWidget
        """)


@importorskip('keyring')
def test_keyring(pyi_builder):
    pyi_builder.test_script('pyi_lib_keyring.py')


@importorskip('lxml')
def test_lxml_isoschematron(pyi_builder):
    pyi_builder.test_source(
        """
        # The import of this module triggers the loading some required XML files.
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


@importorskip('scipy')
def test_scipy(pyi_builder):
    pyi_builder.test_source(
        """
        # General SciPy import.
        from scipy import *
        # Test import hooks for the following modules.
        import scipy.io.matlab
        import scipy.sparse.csgraph
        # Some other "problematic" scipy submodules.
        import scipy.lib
        import scipy.linalg
        import scipy.signal
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

# matplotlib tries to import any of PyQt4, PyQt5 or PySide. But if we
# have more then one of these in the frozen app, the app's
# runtime-hooks will crash. Thus we need to exclude the other two.
all_qt_pkgs = ['PyQt4', 'PyQt5', 'PySide']
excludes = []
for pkg in all_qt_pkgs:
    p = [p for p in all_qt_pkgs]
    p = importorskip(pkg)(p)
    excludes.append(p)

@importorskip('matplotlib')
@pytest.mark.parametrize("excludes", excludes, ids=all_qt_pkgs)
def test_matplotlib(pyi_builder, excludes):
    pyi_args = ['--exclude-module=%s' % e for e in excludes]
    pyi_builder.test_source(
        """
        import os
        import matplotlib
        import sys
        import tempfile
        # In frozen state rthook should force matplotlib to create config directory
        # in temp directory and not $HOME/.matplotlib.
        configdir = os.environ['MPLCONFIGDIR']
        print(('MPLCONFIGDIR: %s' % configdir))
        if not configdir.startswith(tempfile.gettempdir()):
            raise SystemExit('MPLCONFIGDIR not pointing to temp directory.')
        # matplotlib data directory should point to sys._MEIPASS.
        datadir = os.environ['MATPLOTLIBDATA']
        print(('MATPLOTLIBDATA: %s' % datadir))
        if not datadir.startswith(sys._MEIPASS):
            raise SystemExit('MATPLOTLIBDATA not pointing to sys._MEIPASS.')
        # This import was reported to fail with matplotlib 1.3.0.
        from mpl_toolkits import axes_grid1
        """, pyi_args=pyi_args)

del all_qt_pkgs, excludes


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


@importorskip('gi.repository.Gio')
def test_gi_gio_binding(pyi_builder):
    pyi_builder.test_source(
        """
        import gi
        gi.require_version('Gio', '2.0')
        from gi.repository import Gio
        print(Gio)
        """)


@importorskip('gi.repository.GLib')
def test_gi_glib_binding(pyi_builder):
    pyi_builder.test_source(
        """
        import gi
        gi.require_version('GLib', '2.0')
        from gi.repository import GLib
        print(GLib)
        """)


@importorskip('gi.repository.GModule')
def test_gi_gmodule_binding(pyi_builder):
    pyi_builder.test_source(
        """
        import gi
        gi.require_version('GModule', '2.0')
        from gi.repository import GModule
        print(GModule)
        """)


@importorskip('gi.repository.GObject')
def test_gi_gobject_binding(pyi_builder):
    pyi_builder.test_source(
        """
        import gi
        gi.require_version('GObject', '2.0')
        from gi.repository import GObject
        print(GObject)
        """)


@importorskip('gi.repository.Gst')
def test_gi_gst_binding(pyi_builder):
    pyi_builder.test_source(
        """
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        Gst.init(None)
        print(Gst)
        """)


@importorskip('PIL')
@pytest.mark.xfail(reason="Fails with Pillow 3.0.0")
def test_pil_img_conversion(pyi_builder_spec):
    pyi_builder_spec.test_spec('pyi_lib_PIL_img_conversion.spec')


@importorskip('PIL', 'FixTk')
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

@importorskip('PIL.ImageQt', 'PyQt5')
def test_pil_PyQt5(pyi_builder):
    # hook-PIL is excluding PyQt5, but is must still be included
    # since it is imported elsewhere. Also see issue #1584.
    pyi_builder.test_source("""
    import PyQt5
    import PIL
    import PIL.ImageQt
    """)

@importorskip('PIL.ImageQt', 'PyQt4')
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
