#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import argparse

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('info_file', metavar='info-file',
                        help="text file containing version info")
    parser.add_argument('exe_file', metavar='exe-file',
                        help="full pathname of a Windows executable")
    args = parser.parse_args()

    info_file = os.path.abspath(args.info_file)
    exe_file = os.path.abspath(args.exe_file)

    try:
        import PyInstaller.utils.win32.versioninfo
        vs = PyInstaller.utils.win32.versioninfo.SetVersion(exe_file, info_file)
        print(('Version info set in: %s' % exe_file))
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")

if __name__ == '__main__':
    run()
