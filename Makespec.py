#! /usr/bin/env/python
# Automatically build spec files containing a description of the project
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

import sys, os, string

# For Python 1.5 compatibility
try:
    True
except:
    True,False = 1,0

freezetmplt = """\
a = Analysis(%(scripts)s,
             pathex=%(pathex)s)
pyz = PYZ(a.pure)
exe = EXE(%(tkpkg)s pyz,
          a.scripts,
          a.binaries,
          name='%(exename)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
""" # pathex scripts exename tkpkg debug console

collecttmplt = """\
a = Analysis(%(scripts)s,
             pathex=%(pathex)s)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='%(builddir)s/%(exename)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
coll = COLLECT(%(tktree)s exe,
               a.binaries,
               strip=%(strip)s,
               upx=%(upx)s,
               name='%(distdir)s')
""" # scripts pathex, exename, debug, console tktree distdir

comsrvrtmplt = """\
a = Analysis(%(scripts)s,
             pathex=%(pathex)s)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name='%(builddir)s/%(exename)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
dll = DLL(pyz,
          a.scripts,
          exclude_binaries=1,
          name='%(builddir)s/%(dllname)s',
          debug=%(debug)s)
coll = COLLECT(exe, dll,
               a.binaries,
               strip=%(strip)s,
               upx=%(upx)s,
               name='%(distdir)s')
""" # scripts pathex, exename, debug, console tktree distdir
HOME = os.path.dirname(sys.argv[0])
if HOME == '':
    HOME = os.getcwd()
if not os.path.isabs(HOME):
    HOME = os.path.abspath(HOME)
iswin = sys.platform[:3] == "win"
cygwin = sys.platform == "cygwin"
try:
    config = eval(open(os.path.join(HOME, 'config.dat'), 'r').read())
except IOError:
    print "You must run Configure.py before building!"
    sys.exit(1)

if config['pythonVersion'] != sys.version:
    print "The current version of Python is not the same with which PyInstaller was configured."
    print "Please re-run Configure.py with this version."
    sys.exit(1)

def quote_win_filepath( path ):
    # quote all \ with another \ after using normpath to clean up the path
    return string.join( string.split( os.path.normpath( path ), '\\' ), '\\\\' )

# Support for trying to avoid hard-coded paths in the .spec files.
# Eg, all files rooted in the Installer directory tree will be
# written using "HOMEPATH", thus allowing this spec file to
# be used with any Installer installation.
# Same thing could be done for other paths too.
path_conversions = (
    (HOME, "HOMEPATH"),
    # Add Tk etc?
    )

def make_variable_path(filename, conversions = path_conversions):
    for (from_path, to_name) in conversions:
        assert os.path.abspath(from_path)==from_path, \
            "path '%s' should already be absolute" % (from_path,)
        if filename[:len(from_path)] == from_path:
            rest = filename[len(from_path):]
            if rest[0] in "\\/":
                rest = rest[1:]
            return to_name, rest
    return None, filename

# An object used in place of a "path string" which knows how to repr()
# itself using variable names instead of hard-coded paths.
class Path:
    def __init__(self, *parts):
        self.path = apply(os.path.join, parts)
        self.variable_prefix = self.filename_suffix = None
    def __repr__(self):
        if self.filename_suffix is None:
            self.variable_prefix, self.filename_suffix = make_variable_path(self.path)
        if self.variable_prefix is None:
            return repr(self.path)
        return "os.path.join(" + self.variable_prefix + "," + repr(self.filename_suffix) + ")"

def main(scripts, name=None, tk=0, freeze=0, console=1, debug=0, strip=0, upx=0,
         comserver=0, ascii=0, workdir=None, pathex=[], version_file=None, icon_file=None):
    if name is None:
        name = os.path.splitext(os.path.basename(scripts[0]))[0]
    distdir = "dist%s" % name
    builddir = "build%s" % name
    pathex = pathex[:]
    if workdir is None:
        workdir = os.getcwd()
        pathex.append(workdir)
    else:
        pathex.append(os.getcwd())
    if workdir == HOME:
        workdir = os.path.join(HOME, name)
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    exe_options = ''
    if version_file:
        exe_options = "%s, version='%s'" % (exe_options, quote_win_filepath(version_file))
    if icon_file:
        exe_options = "%s, icon='%s'" % (exe_options, quote_win_filepath(icon_file))
    if not ascii and config['hasUnicode']:
        scripts.insert(0, os.path.join(HOME, 'support', 'useUnicode.py'))
    for i in range(len(scripts)):
        scripts[i] = Path(scripts[i]) # Use relative path in specfiles

    d = {'tktree':'',
         'tkpkg' :'',
         'scripts':scripts,
         'pathex' :pathex,
         'exename': '',
         'distdir': distdir,
         'builddir': builddir,
         'debug': debug,
         'strip': strip,
         'upx' : upx,
         'console': console or debug,
         'exe_options': exe_options}
    if tk:
        d['tktree'] = "TkTree(),"
        if freeze:
            scripts.insert(0, Path(HOME, 'support', 'useTK.py'))
            scripts.insert(0, Path(HOME, 'support', 'unpackTK.py'))
            scripts.append(Path(HOME, 'support', 'removeTK.py'))
            d['tkpkg'] = "TkPKG(),"
        else:
            scripts.insert(0, Path(HOME, 'support', 'useTK.py'))
    scripts.insert(0, Path(HOME, 'support', '_mountzlib.py'))
    if iswin or cygwin:
        d['exename'] = name+'.exe'
        d['dllname'] = name+'.dll'
    else:
        d['exename'] = name
        d['console'] = 1
    specfnm = os.path.join(workdir, name+'.spec')
    specfile = open(specfnm, 'w')
    if freeze:
        specfile.write(freezetmplt % d)
    elif comserver:
        specfile.write(comsrvrtmplt % d)
    else:
        specfile.write(collecttmplt % d)
    specfile.close()
    return specfnm

if __name__ == '__main__':
    import optparse
    p = optparse.OptionParser(
        usage="python %prog [opts] <scriptname> [<scriptname> ...]"
    )
    p.add_option("-F", "--onefile", dest="freeze",
                 action="store_true", default=False,
                 help="create a single file deployment")
    p.add_option("-D", "--onedir", dest="freeze", action="store_false",
                 help="create a single directory deployment (default)")
    p.add_option("-w", "--windowed", "--noconsole", dest="console",
                 action="store_false", default=True,
                 help="use a Windows subsystem executable (Windows only)")
    p.add_option("-c", "--nowindowed", "--console", dest="console",
                 action="store_true",
                 help="use a console subsystem executable (Windows only) "
                      "(default)")
    p.add_option("-a", "--ascii", action="store_true", default=False,
                 help="do NOT include unicode encodings "
                      "(default: included if available)")
    p.add_option("-d", "--debug", action="store_true", default=False,
                 help="use the debug (verbose) build of the executable")
    p.add_option("-s", "--strip", action="store_true", default=False,
                 help="strip the exe and shared libs "
                      "(don't try this on Windows)")
    p.add_option("-X", "--upx", action="store_true", default=False,
                 help="use UPX if available (works differently between "
                      "Windows and *nix)")
    p.add_option("-K", "--tk", default=False, action="store_true",
                 help="include TCL/TK in the deployment")
    p.add_option("-o", "--out", type="string", default=None,
                 dest="workdir", metavar="DIR",
                 help="generate the spec file in the specified directory")
    p.add_option("-n", "--name", type="string", default=None,
                 help="name to assign to the project, from which the spec file "
                      "name is generated. (default: use the basename of the "
                      "(first) script)")
    p.add_option("-p", "--paths", type="string", default=[], dest="pathex",
                 metavar="DIR", action="append",
                 help="set base path for import (like using PYTHONPATH). "
                      "Multiple directories are allowed, separating them "
                      "with %s, or using this option multiple times"
                      % repr(os.pathsep))
    p.add_option("-v", "--version", type="string",
                 dest="version_file", metavar="FILE",
                 help="add a version resource from FILE to the exe "
                      "(Windows only)")
    p.add_option("--icon", type="string", dest="icon_file",
                 metavar="FILE.ICO or FILE.EXE,ID",
                 help="If FILE is an .ico file, add the icon to the final "
                      "executable. Otherwise, the syntax 'file.exe,id' to "
                      "extract the icon with the specified id "
                      "from file.exe and add it to the final executable")

    opts,args = p.parse_args()

    # Split pathex by using the path separator
    temppaths = opts.pathex[:]
    opts.pathex = []
    for p in temppaths:
        opts.pathex.extend(string.split(p, os.pathsep))

    if not args:
        p.print_help()
        sys.exit(1)

    nm = apply(main, (args,), opts.__dict__)
    print "wrote %s" % nm
    print "now run Build.py to build the executable"
