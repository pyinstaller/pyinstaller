#!/usr/bin/env python
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
import sys, string, os
if sys.platform[:3] == 'win':
    stripopts = ('',)
    consoleopts = ('', '--noconsole')
else:
    stripopts = ('', '--strip')
    consoleopts = ('',)
if string.find(sys.executable, ' ') > -1:
    exe = '"%s"' % sys.executable
else:
    exe = sys.executable
if sys.platform[:3] == 'win':
    spec = "%s ../../Makespec.py --tk %%s %%s %%s %%s %%s --out t%%d hanoi.py" % exe
    bld = "%s ../../Build.py t%%d/hanoi.spec" % exe
else:
    spec = "%s ../../Makespec.py --tk %%s %%s %%s %%s %%s --out /u/temp/t%%d hanoi.py" % exe
    bld = "%s ../../Build.py /u/temp/t%%d/hanoi.spec" % exe

i = 0
for bldconfig in ('--onedir', '--onefile'):
    for console in consoleopts:
        for dbg in ('--debug', ''):
            for stripopt in stripopts:
                for upxopt in ('', '--upx'):
                    cmd = spec % (bldconfig, console, dbg, stripopt, upxopt, i)
                    os.system(cmd)
                    os.system(bld % i)
                    if sys.platform[:5] == 'linux':
                        if bldconfig == '--onedir':
                            os.system("ln -s /u/temp/t%d/disthanoi/hanoi hanoi%d" % (i,i))
                        else:
                            os.system("ln -s /u/temp/t%d/hanoi hanoi%d" % (i,i))
                    i += 1
