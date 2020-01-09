#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Import hook for Gio https://developer.gnome.org/gio/stable/ from the GLib library https://wiki.gnome.org/Projects/GLib
introspected through PyGobject https://wiki.gnome.org/PyGObject via the GObject Introspection middleware layer
https://wiki.gnome.org/Projects/GObjectIntrospection

Tested with GLib 2.44.1, PyGObject 3.16.2, GObject Introspection 1.44.0 on Mac OS X 10.10.5 and
GLib 2.42.2, PyGObject 3.14.0, and GObject Introspection 1.42 on Windows 7
"""

import glob
import os
import sys

import PyInstaller.log as logging
from PyInstaller.compat import is_darwin, is_win, is_linux, base_prefix
from PyInstaller.utils.hooks import get_gi_typelibs, get_gi_libdir, exec_statement

logger = logging.getLogger(__name__)

binaries, datas, hiddenimports = get_gi_typelibs('Gio', '2.0')

libdir = get_gi_libdir('Gio', '2.0')
path = None

if is_win:
    pattern = os.path.join(libdir, 'gio', 'modules', '*.dll')
elif is_darwin or is_linux:
    gio_libdir = os.path.join(libdir, 'gio', 'modules')
    if not os.path.exists(gio_libdir):
        # homebrew installs the files elsewhere..
        gio_libdir = os.path.join(os.path.commonprefix([base_prefix, gio_libdir]), 'lib', 'gio', 'modules')

    pattern = os.path.join(gio_libdir, '*.so')

if pattern:
    for f in glob.glob(pattern):
        binaries.append((f, 'gio_modules'))
else:
    # To add a new platform add a new elif above with the proper is_<platform> and
    # proper pattern for finding the Gio modules on your platform.
    logger.warning('Bundling Gio modules is currently not supported on your platform.')


# Bundle the mime cache -- might not be needed on Windows
# -> this is used for content type detection (also used by GdkPixbuf)
# -> gio/xdgmime/xdgmime.c looks for mime/mime.cache in the users home directory,
#    followed by XDG_DATA_DIRS if specified in the environment, otherwise
#    it searches /usr/local/share/ and /usr/share/
if not is_win:
    _mime_searchdirs = ['/usr/local/share', '/usr/share']
    if 'XDG_DATA_DIRS' in os.environ:
        _mime_searchdirs.insert(0, os.environ['XDG_DATA_DIRS'])

    for sd in _mime_searchdirs:
        spath = os.path.join(sd, 'mime', 'mime.cache')
        if os.path.exists(spath):
            datas.append((spath, 'share/mime'))
            break
