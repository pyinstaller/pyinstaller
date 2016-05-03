#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for PyGObject's "gi.repository.GdkPixbuf" package.
"""

import glob
import os
import subprocess

from PyInstaller.config import CONF
from PyInstaller.compat import (
    exec_command_stdout, is_darwin, is_win, is_linux, open_file, which)
from PyInstaller.utils.hooks import (
    collect_glib_translations, get_gi_typelibs, get_gi_libdir, logger)

# If the "gdk-pixbuf-query-loaders" command is not in the current ${PATH}, GDK
# and thus GdkPixbuf is unavailable. Return with a non-fatal warning.
if which('gdk-pixbuf-query-loaders') is None:
    logger.warn(
        '"hook-gi.repository.GdkPixbuf" ignored, since GDK not found '
        '(i.e., "gdk-pixbuf-query-loaders" not in $PATH).'
    )
# Else, GDK is available. Let's do this.
else:
    binaries, datas, hiddenimports = get_gi_typelibs('GdkPixbuf', '2.0')
    datas += collect_glib_translations('gdk-pixbuf')

    libdir = get_gi_libdir('GdkPixbuf', '2.0')

    # To add support for a new platform, add a new "elif" branch below with the
    # proper is_<platform>() test and glob for finding loaders on that platform.
    if is_win:
        pattern = os.path.join(
            libdir, 'gdk-pixbuf-2.0', '2.10.0', 'loaders', '*.dll')
    elif is_darwin or is_linux:
        pattern = os.path.join(
            libdir, 'gdk-pixbuf-2.0', '2.10.0', 'loaders', '*.so')

    # If loader detection is supported on this platform, bundle all detected
    # loaders and an updated loader cache.
    if pattern:
        # Bundle all found loaders with this user application.
        for f in glob.glob(pattern):
            binaries.append((f, 'lib/gdk-pixbuf-2.0/2.10.0/loaders'))

        # Filename of the loader cache to be written below.
        cachefile = os.path.join(CONF['workpath'], 'loaders.cache')

        # Run the "gdk-pixbuf-query-loaders" command and capture its standard
        # output providing an updated loader cache; then write this output to
        # the loader cache bundled with this frozen application.
        #
        # If the current platform is OS X...
        if is_darwin:
            # To permit string munging, decode the encoded bytes output by this
            # command (i.e., enable the "universal_newlines" option). Note that:
            #
            # * Under Python 2.7, "cachedata" will be a decoded "unicode" object.
            # * Under Python 3.x, "cachedata" will be a decoded "str" object.
            cachedata = exec_command_stdout('gdk-pixbuf-query-loaders')

            cd = []
            prefix = '"' + libdir
            plen = len(prefix)

            # For each line in the updated loader cache...
            for line in cachedata.splitlines():
                if line.startswith('#'):
                    continue
                if line.startswith(prefix):
                    line = '"@executable_path/lib' + line[plen:]
                cd.append(line)

            # Rejoin these lines in a manner preserving this object's "unicode"
            # type under Python 2.
            cachedata = u'\n'.join(cd)

            # Write the updated loader cache to this file.
            with open_file(cachefile, 'w') as fp:
                fp.write(cachedata)
        # Else, the current platform is *NOT* OS X. In this case, no changes to
        # the loader cache are required. For efficiency and reliability, this
        # command's encoded byte output is written as is without being decoded.
        else:
            with open_file(cachefile, 'wb') as fp:
                fp.write(subprocess.check_output('gdk-pixbuf-query-loaders'))

        # Bundle this loader cache with this frozen application.
        datas.append((cachefile, 'lib/gdk-pixbuf-2.0/2.10.0'))
    # Else, loader detection is unsupported on this platform.
    else:
        logger.warn('GdkPixbuf loader bundling unsupported on your platform.')
