#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import codecs
import os
import argparse

import PyInstaller.utils.win32.versioninfo
import PyInstaller.log


def run():
    PyInstaller.log.init()

    parser = argparse.ArgumentParser(
        epilog = ('The printed output may be saved to a file, edited and '
                  'used as the input for a version resource on any of the '
                  'executable targets in an Installer spec file.'))
    parser.add_argument('exe_file', metavar='exe-file',
                        help="full pathname of a Windows executable")
    parser.add_argument('out_filename', metavar='out-filename', nargs='?',
                        default='file_version_info.txt',
                        help=("filename where the grabbed version info "
                              "will be saved"))

    args = parser.parse_args()

    try:
        vs = PyInstaller.utils.win32.versioninfo.decode(args.exe_file)
        fp = codecs.open(args.out_filename, 'w', 'utf-8')
        fp.write(unicode(vs))
        fp.close()
        print(('Version info written to: %s' % out_filename))
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")

if __name__ == '__main__':
    run()
