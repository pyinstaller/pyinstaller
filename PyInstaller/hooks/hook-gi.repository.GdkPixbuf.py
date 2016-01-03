#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
"""
Import hook for PyGObject https://wiki.gnome.org/PyGObject
"""

import glob
import os
import subprocess

from PyInstaller.config import CONF
from PyInstaller.compat import is_darwin, is_win, is_linux
from PyInstaller.utils.hooks import collect_glib_translations, get_gi_typelibs,\
    get_gi_libdir

binaries, datas, hiddenimports = get_gi_typelibs('GdkPixbuf', '2.0')
datas += collect_glib_translations('gdk-pixbuf')

libdir = get_gi_libdir('GdkPixbuf', '2.0')
if is_win:
    pattern = os.path.join(libdir, 'gdk-pixbuf-2.0', '2.10.0', 'loaders', '*.dll')
elif is_darwin or is_linux:
    pattern = os.path.join(libdir, 'gdk-pixbuf-2.0', '2.10.0', 'loaders', '*.so')

if pattern:
    for f in glob.glob(pattern):
        binaries.append((f, 'lib/gdk-pixbuf-2.0/2.10.0/loaders'))
    
    # Create an updated version of the loader cache
    cachedata = subprocess.check_output('gdk-pixbuf-query-loaders')
    
    if is_darwin:
        cd = []
        prefix = '"' + libdir
        plen = len(prefix)
        
        # TODO: python3 probably will break here
        for line in cachedata.splitlines():
            if line.startswith('#'):
                continue
            if line.startswith(prefix):
                line = '"@executable_path/lib' + line[plen:]
            cd.append(line)
            
        cachedata = '\n'.join(cd)
    
    cachefile = os.path.join(CONF['workpath'], 'loaders.cache')
    with open(cachefile, 'w') as fp:
        fp.write(cachedata)
    
    datas.append((cachefile, 'lib/gdk-pixbuf-2.0/2.10.0'))
else:
    # To add a new platform add a new elif above with the proper is_<platform> and
    # proper pattern for finding the loaders on your platform.
    logger.warn('Bundling GdkPixbuf loaders is currently not supported on your platform.')
