#
# Copyright (C) 2012, Daniel Hyams
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


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
