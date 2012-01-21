#!/usr/bin/env python
# Copyright (C) 2011, Hartmut Goebel
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 1999, 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import optparse
import shutil

try:
    import PyInstaller
except ImportError:
    # if importing PyInstaller fails, try to load from parent
    # directory to support running without installation
    import imp
    import os
    if not hasattr(os, "getuid") or os.getuid() != 0:
        imp.load_module('PyInstaller', *imp.find_module('PyInstaller',
            [os.path.abspath(os.path.join(__file__, '..','..','..'))]))

from PyInstaller import is_win, is_linux
from PyInstaller import compat

utils_dir = os.path.normpath(os.path.join(__file__, '..', '..', '..', 'utils'))
makespec = os.path.join(utils_dir, 'Makespec.py')
build = os.path.join(utils_dir, 'Build.py')

if is_win:
    stripopts = ('',)
    consoleopts = ('', '--noconsole')
else:
    stripopts = ('', '--strip')
    consoleopts = ('',)

out_pattern = 't%d'
if is_linux:
    import tempfile
    out_pattern = os.path.join(tempfile.gettempdir(), 'hanoi', out_pattern)
dist_pattern_dir = os.path.join(out_pattern, 'dist', 'hanoi', 'hanoi')
dist_pattern_file = os.path.join(out_pattern, 'dist', 'hanoi')

script_name = os.path.abspath(os.path.join(__file__, '..', 'hanoi.py'))

def build_test(cnt, bldconfig, *options, **kwopts):
    options = filter(None, options)
    if kwopts['clean'] and os.path.isdir(out_pattern % cnt):
        # remove/clean the working directory
        shutil.rmtree(out_pattern % cnt)
    compat.exec_python_rc(makespec, script_name,
                          '--out', out_pattern % cnt, bldconfig, *options)
    compat.exec_python_rc(build, os.path.join(out_pattern % cnt, 'hanoi.spec'),
                          '--noconfirm')
    if is_linux:
        # create symlinks
        if os.path.islink('hanoi%d' % cnt):
            os.remove('hanoi%d' % cnt)
        if bldconfig == '--onedir':
            os.symlink(dist_pattern_dir % cnt, 'hanoi%d' % cnt)
        else:
            os.symlink(dist_pattern_file % cnt, 'hanoi%d' % cnt)

parser = optparse.OptionParser('%prog [NUM ...]')
parser.add_option('--clean', action='store_true',
                  help=('Perform clean builds '
                        '(remove target dirs prior to building).'))
opts, args = parser.parse_args()
args = map(int, args)
i = 1
for bldconfig in ('--onedir', '--onefile'):
    for console in consoleopts:
        for dbg in ('--debug', ''):
            for stripopt in stripopts:
                if not args or i in args:
                    build_test(i, bldconfig, console, dbg, stripopt, **opts.__dict__)
                i += 1
