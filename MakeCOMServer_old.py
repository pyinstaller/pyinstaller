# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2002 McMillan Enterprises, Inc.
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
import string, os, sys, win32api, Makespec

modspec = """\
    %(mod)s.%(klass)s._reg_class_spec_ = "%(mod)s.%(klass)s"
    if (not hasattr(%(mod)s.%(klass)s, '_reg_clsctx_') or
        %(mod)s.%(klass)s._reg_clsctx_ & pythoncom.CLSCTX_INPROC):
        %(mod)s.%(klass)s._reg_options_ = {'InprocServer32':
             os.path.abspath(
                 os.path.join(
                     os.path.dirname(sys.executable), "%(dllname)s"))}
""" #mod, klass, dllname
tmplt = """\
import sys
import string
import os
inprocess = getattr(sys, 'frozen', None)
%(modimports)s

register = 0
for i in range(1, len(sys.argv)):
    arg = sys.argv[i]
    if string.find(arg, "reg") > -1:
        register = 1
        if arg == '/unreg':
            sys.argv[i] = '--unregister'
if register:
    import pythoncom
    pythoncom.frozen = 1
%(modspecs)s
    from win32com.server import register
    register.UseCommandLine(%(regspecs)s, %(flags)s)
else:
    #older Python's need to force this import before pythoncom does it
    import win32com.server.policy
    if inprocess == 'dll':
        pass
    else:
        import win32com.server.localserver
        win32com.server.localserver.main()

""" #modimports, modspecs regspecs, flags

def create(scripts, debug, verbosity, workdir, ascii=0):
    infos = []  # (path, module, klasses)
    for script in scripts:
        infos.append(analscriptname(script))
    outfnm = 'drive%s.py' % infos[0][1]
    dllname = 'drive%s.dll' % infos[0][1]
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    outfnm = os.path.join(workdir, outfnm)
    outf = open(outfnm, 'w')
    modspecs = []
    regspecs = []
    modimports = []
    flags = 'debug=0, quiet=%s' % (verbosity==0)
    paths = []
    for path, module, klasses in infos:
        if path:
            paths.append(path)
        for klass in klasses:
            d = { 'mod':module, 'klass':klass, 'dllname':dllname }
            modspecs.append(modspec % d)
            regspecs.append('%(mod)s.%(klass)s' % d)
            modimports.append("import %(mod)s" % d)
    for i in range(len(paths)):
        path = paths[i]
        paths[i] = win32api.GetShortPathName(os.path.normpath(path))
    modspecs = string.join(modspecs, '\n')
    modimports = string.join(modimports, '\n')
    regspecs = string.join(regspecs, ', ')
    d = { 'modspecs':modspecs,
          'regspecs':regspecs,
          'modimports':modimports,
          'flags':flags }
    outf.write( tmplt % d )
    outf.close()
    print "**********************************"
    print "Driver script %s created" % outfnm
    specfnm = Makespec.main([outfnm], console=debug, debug=debug,
                            workdir=workdir, pathex=paths, comserver=1, ascii=ascii)
    print "Spec file %s created" % specfnm

def analscriptname(script):
    # return (path, module, klasses)
    path, basename = os.path.split(script)
    module = os.path.splitext(basename)[0]
    while ispkgdir(path):
        path, basename = os.path.split(path)
        module = '%s.%s' % (basename, module)
    try:
        __import__(module)
    except ImportError:
        oldpath = sys.path[:]
        sys.path.insert(0, path)
        try:
            __import__(module)
        finally:
            sys.path = oldpath
    else:
        path = None
    m = sys.modules[module]
    klasses = []
    for nm, thing in m.__dict__.items():
        if hasattr(thing, '_reg_clsid_'):
            klasses.append(nm)
    return (path, module, klasses)

def ispkgdir(path):
    try:
        open(os.path.join(path, '__init__.py'), 'r')
    except IOError:
        try:
            open(os.path.join(path, '__init__.pyc'), 'rb')
        except IOError:
            return 0
    return 1

usage = """\
Usage: python %s [options] <scriptname>.py [<scriptname>.py ...]
 --debug -> use debug console build and register COM servers with debug
 --verbose -> use verbose flag in COM server registration
 --out dir -> generate script and spec file in dir

The next step is to run Build.py against the generated spec file.
See doc/Tutorial.html for details.
"""

if __name__ == '__main__':
    #scripts, debug, verbosity, workdir
    debug = verbosity = ascii = 0
    workdir = '.'
    import getopt
    opts, args = getopt.getopt(sys.argv[1:], '', ['debug', 'verbose', 'ascii', 'out='])
    for opt, val in opts:
        if opt == '--debug':
            debug = 1
        elif opt == '--verbose':
            verbosity = 1
        elif opt == '--out':
            workdir = val
        elif opt == '--ascii':
            ascii = 1
        else:
            print usage % sys.argv[0]
            sys.exit(1)
    if not args:
        print usage % sys.argv[0]
    else:
        create(args, debug, verbosity, workdir, ascii)
