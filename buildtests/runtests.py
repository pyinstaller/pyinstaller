#!/usr/bin/env python
# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
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

# This program will execute any file with name test*<digit>.py. If your test
# need an aditional dependency name it test*<digit><letter>.py to be ignored
# by this program but be recognizable by any one as a dependency of that
# particual test.

import os, sys, glob, string
import shutil
try:
    here=os.path.dirname(__file__)
except NameError:
    here=os.path.dirname(sys.argv[0])
PYTHON = sys.executable
if sys.platform[:3] == 'win':
    if string.find(PYTHON, ' ') > -1:
        PYTHON='"%s"' % PYTHON

def clean():
    distdirs = glob.glob(os.path.join(here, 'disttest*'))
    for dir in distdirs:
        try:
            shutil.rmtree(dir)
        except OSError, e:
            print e
    builddirs = glob.glob(os.path.join(here, 'buildtest*'))
    for dir in builddirs:
        try:
            shutil.rmtree(dir)
        except OSError, e:
            print e
    wfiles = glob.glob(os.path.join(here, 'warn*.txt'))
    for file in wfiles:
        try:
            os.remove(file)
        except OSError, e:
            print e

def runtests():
    global here
    sources = glob.glob(os.path.join(here, 'test*[0-9].py'))
    path = os.environ["PATH"]
    for src in sources:
        print
        print "################## EXECUTING TEST %s ################################" % src
        print
        test = os.path.splitext(os.path.basename(src))[0]
        os.system('%s ../Build.py %s' % (PYTHON, test+".spec"))
        # Run the test in a clean environment to make sure they're really self-contained
        del os.environ["PATH"]
        os.system('dist%s%s%s' % (test, os.sep, test))
        os.environ["PATH"] = path
        print "################## FINISHING TEST %s  ################################" % src

if __name__ == '__main__':
    if len(sys.argv) == 1:
        clean()
        runtests()
    if '--clean' in sys.argv:
        clean()
    if '--run' in sys.argv:
        runtests()
    raw_input("Press any key to exit")
