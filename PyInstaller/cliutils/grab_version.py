#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import PyInstaller.utils.versioninfo
from PyInstaller.utils import misc


def run():
    misc.check_not_running_as_root()

    if len(sys.argv) < 2:
        print 'Usage: >python GrabVersion.py <exe>'
        print ' where: <exe> is the fullpathname of a Windows executable.'
        print ' The printed output may be saved to a file,  editted and '
        print ' used as the input for a verion resource on any of the '
        print ' executable targets in an Installer config file.'
        print ' Note that only NT / Win2K can set version resources.'
    else:
        try:
            vs = PyInstaller.utils.versioninfo.decode(sys.argv[1])
            print vs
        except KeyboardInterrupt:
            raise SystemExit("Aborted by user request.")
