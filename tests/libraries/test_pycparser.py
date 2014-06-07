#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import os


fnames_to_track = [
    'lextab.py',
    'yacctab.py',
]


def fnames_found():
    return [
        fname for fname in fnames_to_track
        if os.path.isfile(fname)
    ]


if __name__ == '__main__':

    # Confirm no files exist before we start.
    if fnames_found():
        sys.exit('FAIL: Files present before test.')

    # Minimal invocation that generates the files.
    from pycparser import c_parser
    parser = c_parser.CParser()

    # Were the files generated?
    fnames_generated = fnames_found()

    # Try to remove them, if so.
    for fname in fnames_generated:
        try:
            os.unlink(fname)
        except OSError:
            pass

    # Did we fail at deleting any file?
    fnames_left = fnames_found()

    # Fail if any file was generated.
    if fnames_generated:
        if fnames_left:
            sys.exit('FAIL: Files generated and not removed.')
        else:
            sys.exit('FAIL: Files generated but removed.')

    # Success.
    sys.exit(0)

