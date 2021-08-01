#-----------------------------------------------------------------------------
# Copyright (c) 2019-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import os
import sys

if len(sys.argv) > 1:
    basedir = os.path.dirname(sys.executable)
    # if script is inside .app package
    if os.path.basename(basedir) == 'MacOS':
        basedir = os.path.abspath(os.path.join(basedir, os.pardir, os.pardir, os.pardir))

    logfile = os.path.join(basedir, 'args.log')
    with open(logfile, 'w') as file:
        for arg in sys.argv[1:]:
            file.write(arg)
