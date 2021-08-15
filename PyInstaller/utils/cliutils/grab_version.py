#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import argparse
import codecs


def run():
    parser = argparse.ArgumentParser(
        epilog=(
            'The printed output may be saved to a file, edited and used as the input for a version resource on any of '
            'the executable targets in a PyInstaller .spec file.'
        )
    )
    parser.add_argument(
        'exe_file',
        metavar='exe-file',
        help="full pathname of a Windows executable",
    )
    parser.add_argument(
        'out_filename',
        metavar='out-filename',
        nargs='?',
        default='file_version_info.txt',
        help="filename where the grabbed version info will be saved",
    )

    args = parser.parse_args()

    try:
        import PyInstaller.utils.win32.versioninfo
        vs = PyInstaller.utils.win32.versioninfo.decode(args.exe_file)
        if not vs:
            raise SystemExit("Error: VersionInfo resource not found in exe")
        with codecs.open(args.out_filename, 'w', 'utf-8') as fp:
            fp.write(str(vs))
        print('Version info written to: %s' % args.out_filename)
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")


if __name__ == '__main__':
    run()
