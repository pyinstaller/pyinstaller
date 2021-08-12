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
"""
Import hook for PyGObject's "gi.repository.GdkPixbuf" package.
"""

import glob
import os
from shutil import which

from PyInstaller.compat import exec_command_stdout, is_darwin, is_linux, is_win
from PyInstaller.config import CONF
from PyInstaller.utils.hooks import get_hook_config, logger
from PyInstaller.utils.hooks.gi import (collect_glib_translations, get_gi_libdir, get_gi_typelibs)

loaders_path = os.path.join('gdk-pixbuf-2.0', '2.10.0', 'loaders')

destpath = "lib/gdk-pixbuf/loaders"
cachedest = "lib/gdk-pixbuf"

# If the "gdk-pixbuf-query-loaders" command is not in the current ${PATH}, or is not in the GI lib path, GDK and thus
# GdkPixbuf is unavailable. Return with a non-fatal warning.
gdk_pixbuf_query_loaders = None

try:
    libdir = get_gi_libdir('GdkPixbuf', '2.0')
except ValueError:
    logger.warning('"hook-gi.repository.GdkPixbuf" ignored, since GdkPixbuf library not found')
    libdir = None

if libdir:
    # Distributions either package gdk-pixbuf-query-loaders in the GI libs directory (not on the path), or on the path
    # with or without a -x64 suffix depending on the architecture
    cmds = [
        os.path.join(libdir, 'gdk-pixbuf-2.0/gdk-pixbuf-query-loaders'),
        'gdk-pixbuf-query-loaders-64',
        'gdk-pixbuf-query-loaders',
    ]

    for cmd in cmds:
        gdk_pixbuf_query_loaders = which(cmd)
        if gdk_pixbuf_query_loaders is not None:
            break

    if gdk_pixbuf_query_loaders is None:
        logger.warning(
            '"hook-gi.repository.GdkPixbuf" ignored, since "gdk-pixbuf-query-loaders" is not in $PATH or gi lib dir.'
        )

    # Else, GDK is available. Let's do this.
    else:
        binaries, datas, hiddenimports = get_gi_typelibs('GdkPixbuf', '2.0')

        # To add support for a new platform, add a new "elif" branch below with the proper is_<platform>() test and glob
        # for finding loaders on that platform.
        if is_win:
            ext = "*.dll"
        elif is_darwin or is_linux:
            ext = "*.so"

        # If loader detection is supported on this platform, bundle all detected loaders and an updated loader cache.
        if ext:
            loader_libs = []

            # Bundle all found loaders with this user application.
            pattern = os.path.join(libdir, loaders_path, ext)
            for f in glob.glob(pattern):
                binaries.append((f, destpath))
                loader_libs.append(f)

            # Sometimes the loaders are stored in a different directory from the library (msys2)
            if not loader_libs:
                pattern = os.path.join(libdir, '..', 'lib', loaders_path, ext)
                for f in glob.glob(pattern):
                    binaries.append((f, destpath))
                    loader_libs.append(f)

            # Filename of the loader cache to be written below.
            cachefile = os.path.join(CONF['workpath'], 'loaders.cache')

            # Run the "gdk-pixbuf-query-loaders" command and capture its standard output providing an updated loader
            # cache; then write this output to the loader cache bundled with this frozen application. On all platforms,
            # we also move the package structure to point to lib/gdk-pixbuf instead of lib/gdk-pixbuf-2.0/2.10.0 in
            # order to make compatible for OSX application signing.
            #
            # On Mac OS we use @executable_path to specify a path relative to the generated bundle. However, on
            # non-Windows, we need to rewrite the loader cache because it is not relocatable by default. See
            # https://bugzilla.gnome.org/show_bug.cgi?id=737523
            #
            # To make it easier to rewrite, we just always write @executable_path, since its significantly easier to
            # find/replace at runtime. :)
            #
            # To permit string munging, decode the encoded bytes output by this command (i.e., enable the
            # "universal_newlines" option).
            #
            # On Fedora, the default loaders cache is /usr/lib64, but the libdir is actually /lib64. To get around this,
            # we pass the path to the loader command, and it will create a cache with the right path.
            #
            # On Windows, the loaders lib directory is relative, starts with 'lib', and uses \\ as path separators
            # (escaped \).
            cachedata = exec_command_stdout(gdk_pixbuf_query_loaders, *loader_libs)

            cd = []
            prefix = '"' + os.path.join(libdir, 'gdk-pixbuf-2.0', '2.10.0')
            plen = len(prefix)

            win_prefix = '"' + '\\\\'.join(['lib', 'gdk-pixbuf-2.0', '2.10.0'])
            win_plen = len(win_prefix)

            # For each line in the updated loader cache...
            for line in cachedata.splitlines():
                if line.startswith('#'):
                    continue
                if line.startswith(prefix):
                    line = '"@executable_path/' + cachedest + line[plen:]
                elif line.startswith(win_prefix):
                    line = '"' + cachedest.replace('/', '\\\\') + line[win_plen:]
                cd.append(line)

            cachedata = '\n'.join(cd)

            # Write the updated loader cache to this file.
            with open(cachefile, 'w') as fp:
                fp.write(cachedata)

            # Bundle this loader cache with this frozen application.
            datas.append((cachefile, cachedest))
        # Else, loader detection is unsupported on this platform.
        else:
            logger.warning('GdkPixbuf loader bundling unsupported on your platform.')


def hook(hook_api):
    hook_datas = []
    lang_list = get_hook_config(hook_api, "gi", "languages")

    if libdir and gdk_pixbuf_query_loaders is not None:
        hook_datas += collect_glib_translations('gdk-pixbuf', lang_list)
    hook_api.add_datas(hook_datas)
