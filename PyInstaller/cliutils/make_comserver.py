#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from __future__ import print_function

import optparse
import os
import sys

import PyInstaller
try:
    import win32api
except ImportError:
    # Avoid raising an import error on other platforms, so we can run
    # the script to get the usage message.
    if PyInstaller.is_win:
        raise

import PyInstaller.makespec
from PyInstaller.utils import misc


tmplt = '''\
import sys
import os
import pythoncom
pythoncom.frozen = 1
inprocess = getattr(sys, "frozen", None)

%(modules)s
klasses = (%(klasses)s,)

def DllRegisterServer():
    import win32com.server.register
    win32com.server.register.RegisterClasses(*klasses)
    return 0

def DllUnregisterServer():
    import win32com.server.register
    win32com.server.register.UnregisterClasses(*klasses)
    return 0

if sys.frozen != "dll":
    import win32com.server.localserver
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i].lower()
        if arg.find("/reg") > -1 or arg.find("--reg") > -1:
            DllRegisterServer()
            break

        if arg.find("/unreg") > -1 or arg.find("--unreg") > -1:
            DllUnregisterServer()
            break

        # MS seems to like /automate to run the class factories.
        if arg.find("/automate") > -1:
            clsids = []
            for k in klasses:
                clsids.append(k._reg_clsid_)
            win32com.server.localserver.serve(clsids)
            break
    else:
        # You could do something else useful here.
        import win32api
        win32api.MessageBox(0,
                            "This program hosts a COM Object and\\r\\n"
                            "is started automatically",
                            "COM Object")
'''


def create(scripts, debug, verbose, workdir, ascii=0):
    infos = []  # (path, module, klasses)
    for script in scripts:
        infos.append(analscriptname(script))
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    outfnm = 'drive%s.py' % infos[0][1]
    outfnm = os.path.join(workdir, outfnm)
    outf = open(outfnm, 'w')
    klassspecs = []
    modimports = []
    flags = 'debug=%s, quiet=%s' % (debug, not verbose)
    paths = []
    for path, module, klasses in infos:
        if path:
            paths.append(win32api.GetShortPathName(os.path.normpath(path)))
        modimports.append("import %s" % (module,))
        for klass in klasses:
            klassspecs.append("%s.%s" % (module, klass))
    modimports = '\n'.join(modimports)
    klassspecs = ', '.join(klassspecs)
    d = {'modules': modimports, 'klasses': klassspecs}
    outf.write(tmplt % d)
    outf.close()
    print("**********************************")
    print("Driver script", outfnm, "created")
    specfnm = PyInstaller.makespec.main([outfnm], console=debug, debug=debug,
            workdir=workdir, pathex=paths, comserver=1, ascii=ascii)
    print("Spec file", specfnm, "created")


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
        open(os.path.join(path, '__init__.py'), 'rU')
    except IOError:
        try:
            open(os.path.join(path, '__init__.pyc'), 'rb')
        except IOError:
            return 0
    return 1

epilog = ("The next step is to run pyi-build against the generated "
          "spec file.")


def run():
    misc.check_not_running_as_root()

    parser = optparse.OptionParser(
        usage='python %s [options] <scriptname>.py [<scriptname>.py ...]',
        epilog="The next step is to run pyi-build against the generated"
               " spec file."
        )
    parser.add_option('--debug', default=False, action='store_true',
            help='Enable bootloader debug messages, and register COM servers with debug')
    parser.add_option('--verbose', default=False, action='store_true',
                      help='Use verbose flag in COM server registration')
    parser.add_option('--out', default='.',
                      metavar='DIR',
                      dest='workdir',
                      help='Where to write the generated script and spec file')
    parser.add_option("-a", "--ascii", action="store_true",
                 help="Do not include unicode encoding support "
                      "(default: included if available)")

    opts, args = parser.parse_args()
    if not args:
        parser.error('Requires at least one script filename')

    try:
        print()
        print(epilog)
    except KeyboardInterrupt:
        raise SystemExit("Aborted by user request.")
