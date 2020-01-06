#-----------------------------------------------------------------------------
# Copyright (c) 2015-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import atexit
import os
import tempfile
import sys

pixbuf_file = os.path.join(sys._MEIPASS, 'lib', 'gdk-pixbuf-2.0', '2.10.0',
                           'loaders.cache')

# If we're not on Windows we need to rewrite the cache
# -> we rewrite on OSX to support --onefile mode
if os.path.exists(pixbuf_file) and sys.platform != 'win32':

    with open(pixbuf_file, 'rb') as fp:
        contents = fp.read()

    # create a temporary file with the cache and cleverly replace the prefix
    # we injected with the actual path
    fd, pixbuf_file = tempfile.mkstemp()
    with os.fdopen(fd, 'wb') as fp:
        libpath = os.path.join(sys._MEIPASS, 'lib').encode('utf-8')
        fp.write(contents.replace(b'@executable_path/lib', libpath))

    try:
        atexit.register(os.unlink, pixbuf_file)
    except OSError:
        pass


os.environ['GDK_PIXBUF_MODULE_FILE'] = pixbuf_file
