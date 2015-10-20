#-----------------------------------------------------------------------------
# Copyright (c) 2014, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Pretty-prints a TOC file.
"""


import codecs
import argparse
import pprint

import PyInstaller.log

def run():
    PyInstaller.log.init()

    parser = argparse.ArgumentParser()
    parser.add_argument('toc_files', metavar='toc-file', nargs='+')
    args = parser.parse_args()

    for toc_file in args.toc_files:
        with codecs.open(toc_file, 'r', 'utf-8') as f:
            from PyInstaller.depend.bindepend import BindingRedirect
            pprint.pprint(eval(f.read()))

if __name__ == '__main__':
    run()
