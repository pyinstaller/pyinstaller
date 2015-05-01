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

import PyInstaller.utils.win32.versioninfo
from PyInstaller.utils import misc




def run():
    misc.check_not_running_as_root()

    out_filename = os.path.abspath('file_version_info.txt')

    if len(sys.argv) < 2:
        print('Usage: python grab_version.py <exe>  [ out.txt ]')
        print(' where: <exe> is the fullpathname of a Windows executable and')
        print(' <out.txt> is the optional pathname where the grabbed')
        print(' version info will be saved.')
        print(' default out filename:  file_version_info.txt')
        print(' The printed output may be saved to a file, edited and')
        print(' used as the input for a version resource on any of the')
        print(' executable targets in an Installer spec file.')
        raise SystemExit(1)

    if len(sys.argv) == 3:
        out_filename = os.path.abspath(sys.argv[2])

    try:
        vs = PyInstaller.utils.win32.versioninfo.decode(sys.argv[1])
        fp = codecs.open(out_filename, 'w', 'utf-8')
        fp.write(unicode(vs))
        fp.close()
        print(('Version info written to: %s' % out_filename))
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
