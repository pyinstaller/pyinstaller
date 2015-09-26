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
import optparse
import pprint

from PyInstaller.utils import misc


def run():
    misc.check_not_running_as_root()

    _, args = optparse.OptionParser(usage='usage: %prog toc_files...').parse_args()

    for toc_file in args:
        with codecs.open(toc_file, 'r', 'utf-8') as f:
            from PyInstaller.depend.bindepend import BindingRedirect
            pprint.pprint(eval(f.read()))
