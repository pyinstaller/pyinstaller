#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import PyInstaller.hooks.hookutils

from PyInstaller.hooks.hookutils import logger


def hook(mod):
    pth = str(mod.__path__[0])
    if os.path.isdir(pth):
        # If the user imported setuparg1, this is detected
        # by the hook-wx.lib.pubsub.setuparg1.py hook. That
        # hook sets PyInstaller.hooks.hookutils.wxpubsub
        # to "arg1", and we set the appropriate path here.
        protocol = getattr(PyInstaller.hooks.hookutils, 'wxpubsub', 'kwargs')
        logger.info('wx.lib.pubsub: Adding %s protocol path' % protocol)
        mod.__path__.append(os.path.normpath(os.path.join(pth, protocol)))

    return mod
