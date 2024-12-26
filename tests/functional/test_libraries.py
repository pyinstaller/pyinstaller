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

import pytest

from PyInstaller.compat import is_win, is_linux
from PyInstaller.utils.tests import importorskip, skipif, requires
from PyInstaller.utils.hooks import can_import_module


@importorskip('gevent')
def test_gevent(pyi_builder):
    pyi_builder.test_source("""
        import gevent
        gevent.spawn(lambda: x)
        """)


@importorskip('gevent')
def test_gevent_monkey(pyi_builder):
    pyi_builder.test_source("""
        from gevent.monkey import patch_all
        patch_all()
        """)


# The tkinter module may be available for import, but not actually importable due to missing shared libraries.
# Therefore, we need to use `can_import_module`-based skip decorator instead of `@importorskip`.
@pytest.mark.skipif(not can_import_module("tkinter"), reason="tkinter cannot be imported.")
def test_tkinter(pyi_builder):
    pyi_builder.test_script('pyi_lib_tkinter.py')


# In contrast to test_tkinter, which performs basic import test and verifies that the environment variables are properly
# set, this is a full functional test; we try to create a Tk window with label and button, and register a timer to shut
# down the application. Doing so verifies that all Tcl/Tk files (e.g., .tcl scripts from library directories) are
# properly collected.
#
# The prerequisite for this test is that tkinter can be used unfrozen, so try instantiating a window in a subprocess
# to verify that this is the case. This check should cover the following scenarios:
#  - tkinter missing
#  - import of tkinter crashes python interpreter
#  - tkinter.Tk() fails due to DISPLAY not being set on linux
#  - tkinter.Tk() fails due to faulty build (e.g., due to Tcl/Tk version mix-up, as seen with python <= 3.10 builds on
#    macos-12 GHA runners; https://github.com/actions/setup-python/issues/649#issuecomment-1745056485)
def _tkinter_fully_usable():
    from PyInstaller import isolated

    @isolated.decorate
    def _create_tkinter_window():
        import tkinter
        tkinter.Tk()

    try:
        _create_tkinter_window()
    except Exception:
        return False

    return True


def test_tkinter_functional(pyi_builder):
    if not _tkinter_fully_usable():
        pytest.skip("tkinter is not fully usable.")

    pyi_builder.test_source(
        """
        import tkinter
        import tkinter.messagebox

        root = tkinter.Tk()

        # Dump information about library/data directory.
        tcl_dir = root.tk.exprstring('$tcl_library')
        print(f"Run-time Tcl library/data directory: {tcl_dir}")

        tk_dir = root.tk.exprstring('$tk_library')
        print(f"Run-time Tk library/data directory: {tk_dir}")

        # Create test GUI
        label = tkinter.Label(root, text="Hello World")
        label.pack()

        def test_button_callback():
            tkinter.messagebox.showinfo("Test", "Test message")

        button = tkinter.Button(root, text="Test button", command=test_button_callback)
        button.pack()

        def shutdown_timer_callback():
            print("Shutting down!")
            root.destroy()

        shutdown_interval = 1000  # ms
        print(f"Starting shutdown timer ({shutdown_interval} ms)...")
        root.after(shutdown_interval, shutdown_timer_callback)

        print("Entering main loop...")
        root.mainloop()

        print("Done!")
    """
    )


@importorskip('sphinx')
def test_sphinx(pyi_builder, data_dir):
    pyi_builder.test_script(
        'pyi_lib_sphinx.py',
        # Pass the path to temporary copy of data directory via command-line arguments.
        app_args=[str(data_dir)],
    )


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
        """
    )


@requires('zope.interface')
def test_zope_interface(pyi_builder):
    # Tests that `nspkg.pth`-based namespace package are bundled properly. The `nspkg.pth` file is created by
    # setuptools and thus changes frequently. If this test fails, most probably _SETUPTOOLS_NAMESPACEPKG_PTHs
    # in modulegraph needs to be updated.
    pyi_builder.test_source(
        """
        # Package 'zope' does not contain __init__.py file.
        # Just importing 'zope.interface' is sufficient.
        import zope.interface
        """
    )


# The tkinter module may be available for import, but not actually importable due to missing shared libraries.
# Therefore, we need to use `can_import_module`-based skip decorator instead of `@importorskip`.
@importorskip('idlelib')
@pytest.mark.skipif(not can_import_module("tkinter"), reason="tkinter cannot be imported.")
def test_idlelib(pyi_builder):
    pyi_builder.test_source(
        """
        # This file depends on loading some icons, located based on __file__.
        import idlelib.tree
        """
    )


@importorskip('keyring')
@skipif(
    is_linux,
    reason="SecretStorage backend on linux requires active D-BUS session and initialized keyring, and may "
    "need to unlock the keyring via UI prompt."
)
def test_keyring(pyi_builder):
    pyi_builder.test_source("""
        import keyring
        keyring.get_password("test", "test")
        """)


@importorskip('numpy')
def test_numpy(pyi_builder):
    pyi_builder.test_source(
        """
        import numpy
        from numpy.core.numeric import dot
        print('dot(3, 4):', dot(3, 4))
        """
    )


@importorskip('pytz')
def test_pytz(pyi_builder):
    pyi_builder.test_source("""
        import pytz
        pytz.timezone('US/Eastern')
        """)


@importorskip('requests')
def test_requests(pyi_builder, data_dir):
    # NOTE: including the `data_dir` fixture copies files needed by this test!
    # We collect the data into frozen application.
    add_data_arg = f"{data_dir / '*'}:."
    pyi_builder.test_script('pyi_lib_requests.py', pyi_args=['--add-data', add_data_arg])


@importorskip('urllib3.packages.six')
def test_urllib3_six(pyi_builder):
    # Test for pre-safe-import urllib3.packages.six.moves.
    pyi_builder.test_source(
        """
        import urllib3.connectionpool
        import types
        assert isinstance(urllib3.connectionpool.queue, types.ModuleType)
        """
    )


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
        """
    )


@requires('scapy >= 2.0')
def test_scapy(pyi_builder):
    pyi_builder.test_source(
        """
        # Test-cases taken from issue #834
        import scapy.all
        scapy.all.IP

        from scapy.all import IP

        # Test-case taken from issue #202.
        from scapy.all import *
        DHCP  # scapy.layers.dhcp.DHCP
        BOOTP  # scapy.layers.dhcp.BOOTP
        DNS  # scapy.layers.dns.DNS
        ICMP  # scapy.layers.inet.ICMP
        """
    )


@requires('scapy >= 2.0')
def test_scapy2(pyi_builder):
    pyi_builder.test_source(
        """
        # Test the hook to scapy.layers.all
        from scapy.layers.all import DHCP
        """
    )


@requires('scapy >= 2.0')
def test_scapy3(pyi_builder):
    pyi_builder.test_source(
        """
        # Test whether
        # a) scapy packet layers are not included if neither scapy.all nor scapy.layers.all are imported
        # b) packages are included if imported explicitly

        NAME = 'hook-scapy.layers.all'
        layer_inet = 'scapy.layers.inet'

        def testit():
            try:
                __import__(layer_inet)
                raise SystemExit('Self-test of hook %s failed: package module found'
                                 % NAME)
            except ImportError, e:
                if not e.args[0].endswith(' inet'):
                    raise SystemExit('Self-test of hook %s failed: package module found and has import errors: %r'
                                     % (NAME, e))

        import scapy
        testit()
        import scapy.layers
        testit()
        # Explicitly import a single layer module. Note: This module MUST NOT import inet (neither directly nor
        # indirectly), otherwise the test above fails.
        import scapy.layers.ir
        """
    )


@importorskip('sqlalchemy')
def test_sqlalchemy(pyi_builder):
    pyi_builder.test_source(
        """
        # The hook behaviour is to include with sqlalchemy all installed database backends.
        import sqlalchemy
        # This import was known to fail with sqlalchemy 0.9.1
        import sqlalchemy.ext.declarative
        """
    )


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
        # Applications importing module twisted.internet.reactor might fail with error like:
        #
        #     AttributeError: 'module' object has no attribute 'listenTCP'
        #
        # Ensure default reactor was loaded - it has method 'listenTCP' to start server.
        if not hasattr(reactor, 'listenTCP'):
            raise SystemExit('Twisted reactor not properly initialized.')
        """
    )


@importorskip('pyexcelerate')
def test_pyexcelerate(pyi_builder):
    pyi_builder.test_source(
        """
        # Requires PyExcelerate 0.6.1 or higher
        # Tested on Windows 7 x64 SP1 with CPython 2.7.6
        import pyexcelerate
        """
    )


@importorskip('usb')
@pytest.mark.skipif(is_linux, reason='libusb_exit segfaults on some linuxes')
def test_usb(pyi_builder):
    # See if the usb package is supported on this platform.
    try:
        import usb
        # This will verify that the backend is present; if not, it will skip this test.
        usb.core.find()
    except (ImportError, usb.core.NoBackendError):
        pytest.skip('USB backnd not found.')

    pyi_builder.test_source(
        """
        import usb.core
        # NoBackendError fails the test if no backends are found.
        usb.core.find()
        """
    )


@importorskip('zeep')
def test_zeep(pyi_builder):
    pyi_builder.test_source(
        """
        # Test the hook to zeep
        from zeep import utils
        utils.get_version()
        """
    )


@importorskip('pandas')
def test_pandas_extension(pyi_builder):
    # Tests that the C extension ``pandas._libs.lib`` is properly bundled. Issue #1580.
    # See http://pandas.pydata.org/pandas-docs/stable/whatsnew.html#modules-privacy-has-changed.
    pyi_builder.test_source(
        """
        from pandas._libs.lib import is_float
        assert is_float(1) == 0
        """
    )


@importorskip('pandas')
@importorskip('jinja2')
def test_pandas_io_formats_style(pyi_builder):
    # pandas.io.formats.style requires jinja2 as hiddenimport, as well as collected template file
    # from pandas/io/formats/templates. See #6008 and #6009.
    pyi_builder.test_source("""
        import pandas.io.formats.style
        """)


@importorskip('pandas')
@importorskip('matplotlib')
def test_pandas_plotting_matplotlib(pyi_builder):
    # Test that pandas.plotting works. Starting with pandas 1.3.0, the used pandas.plotting._matplotlib backend module
    # is loaded via importlib.import_module(), and needs a hidden import. See #5994.
    pyi_builder.test_source(
        """
        import matplotlib as mpl
        import pandas as pd

        mpl.use('Agg')  # Use headless Agg backend to avoid dependency on display server.

        series = pd.Series([0, 1, 2, 3], [0, 1, 2, 3])
        series.plot()
        """
    )


@importorskip('win32ctypes')
@pytest.mark.skipif(not is_win, reason='pywin32-ctypes is supported only on Windows')
@pytest.mark.parametrize('submodule', ['win32api', 'win32cred', 'pywintypes'])
def test_pywin32ctypes(pyi_builder, submodule):
    pyi_builder.test_source(f"""
        from win32ctypes.pywin32 import {submodule}
        """)


@importorskip('setuptools')
def test_setuptools(pyi_builder):
    pyi_builder.test_source("""
        import setuptools
        """)


@importorskip('babel')
def test_babel(pyi_builder):
    # Try to format a date/time in order to ensure that data files from babel's locale-data directory (especially
    # root.dat) can be unpickled.
    pyi_builder.test_source(
        """
        import datetime
        from babel.dates import format_datetime

        datetime_obj = datetime.datetime(2007, 4, 1, 15, 30)
        print(format_datetime(datetime_obj, 'full', locale='fr_FR'))
        """
    )
