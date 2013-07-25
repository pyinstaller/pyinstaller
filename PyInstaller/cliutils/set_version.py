#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import codecs
import os
import sys

import PyInstaller.utils.versioninfo
from PyInstaller.utils import misc


def run():
    misc.check_not_running_as_root()

    out_filename = os.path.abspath('file_version_info.txt')

    if len(sys.argv) < 3:
        print 'Usage: python set_version.py  <version_info.txt>  <exe>'
        print ' where: <version_info.txt> is file containing version info'
        print ' and <exe> is the fullpathname of a Windows executable.'
        raise SystemExit(1)

    info_file = os.path.abspath(sys.argv[1])
    exe_file = os.path.abspath(sys.argv[2])

    try:
        vs = PyInstaller.utils.versioninfo.SetVersion(exe_file, info_file)
        print('Version info set in: %s' % exe_file)
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
