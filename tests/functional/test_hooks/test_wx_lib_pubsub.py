#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

"""
Functional tests for the PyPubSub API bundled with wxPython.

Since wxPython is currently only stably supported under Python 2, these tests
are implicitly skipped under Python 3.
"""

from PyInstaller.utils.tests import importorskip, xfail_py3


@xfail_py3
@importorskip('wx.lib.pubsub')
def test_wx_lib_pubsub_protocol_default(pyi_builder):
    """
    Functional test applicable to all PyPubSub versions.
    """
    pyi_builder.test_script('pyi_hooks/wx_lib_pubsub.py')

@xfail_py3
@importorskip('wx.lib.pubsub.core')
def test_wx_lib_pubsub_protocol_kwargs(pyi_builder):
    """
    Functional test specific to version 3 of the PyPubSub API.

    The `wx.lib.pubsub.core` package is specific to this version.
    """
    pyi_builder.test_script('pyi_hooks/wx_lib_pubsub_setupkwargs.py')

@xfail_py3
@importorskip('wx.lib.pubsub.core')
def test_wx_lib_pubsub_protocol_arg1(pyi_builder):
    """
    Functional test specific to version 3 of the PyPubSub API.

    The `wx.lib.pubsub.core` package is specific to this version.
    """
    pyi_builder.test_script('pyi_hooks/wx_lib_pubsub_setuparg1.py')
