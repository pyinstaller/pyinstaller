#!/usr/bin/env python
#
# Automatically build spec files containing a description of the project
#
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

import sys, os

from PyInstaller import HOMEPATH, CONFIGDIR, DEFAULT_CONFIGFILE
from PyInstaller import is_win, is_cygwin, is_darwin


onefiletmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             hookspath=%(hookspath)r)
pyz = PYZ(a.pure)
exe = EXE(%(tkpkg)s pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=os.path.join(%(distdir)s, '%(exename)s'),
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
""" # pathex scripts exename tkpkg debug console distdir

onedirtmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             hookspath=%(hookspath)r)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join(%(builddir)s, '%(exename)s'),
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
coll = COLLECT(%(tktree)s exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=%(strip)s,
               upx=%(upx)s,
               name=os.path.join(%(distdir)s, '%(name)s'))
""" # scripts pathex, exename, debug, console tktree distdir name

comsrvrtmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             hookspath=%(hookspath)r)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join(%(builddir)s, '%(exename)s'),
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
dll = DLL(pyz,
          a.scripts,
          exclude_binaries=1,
          name=os.path.join(%(builddir)s, '%(dllname)s'),
          debug=%(debug)s)
coll = COLLECT(exe, dll,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=%(strip)s,
               upx=%(upx)s,
               name=os.path.join(%(distdir)s, '%(name)s'))
""" # scripts pathex, exename, debug, console tktree distdir name

bundleexetmplt = """app = BUNDLE(exe,
             name=os.path.join(%(distdir)s, '%(exename)s.app'))
""" # distdir exename

bundletmplt = """app = BUNDLE(coll,
             name=os.path.join(%(distdir)s, '%(name)s.app'))
""" # distdir name


def quote_win_filepath( path ):
    # quote all \ with another \ after using normpath to clean up the path
    return os.path.normpath(path).replace('\\', '\\\\')

# Support for trying to avoid hard-coded paths in the .spec files.
# Eg, all files rooted in the Installer directory tree will be
# written using "HOMEPATH", thus allowing this spec file to
# be used with any Installer installation.
# Same thing could be done for other paths too.
path_conversions = (
    (HOMEPATH, "HOMEPATH"),
    # For useUnicode.py and useTk.py
    (CONFIGDIR, "CONFIGDIR"),
    # Add Tk etc?
    )

def make_variable_path(filename, conversions = path_conversions):
    for (from_path, to_name) in conversions:
        assert os.path.abspath(from_path)==from_path, (
            "path '%s' should already be absolute" % from_path)
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


def __add_options(parser):
    """
    Add the `Makespec` options to a option-parser instance or a
    option group.
    """
    g = parser.add_option_group('What to generate')
    g.add_option("-F", "--onefile", dest="onefile",
                 action="store_true", default=False,
                 help="create a single file deployment")
    g.add_option("-D", "--onedir", dest="onefile",
                 action="store_false",
                 help="create a single directory deployment (default)")
    g.add_option("-o", "--out",
                 dest="workdir", metavar="DIR",
                 help="generate the spec file in the specified directory "
                      "(default: current directory)")
    g.add_option("-n", "--name",
                 help="name to assign to the project "
                      "(default: first script's basename)")

    g = parser.add_option_group('What to bundle, where to search')
    g.add_option("-p", "--paths", default=[], dest="pathex",
                 metavar="DIR", action="append",
                 help="set base path for import (like using PYTHONPATH). "
                      "Multiple directories are allowed, separating them "
                      "with %s, or using this option multiple times"
                      % repr(os.pathsep))
    g.add_option("--additional-hooks-dir", action="append", dest="hookspath",
                 help="additional path to search for hooks "
                      "(may be given several times)")    
    g.add_option("-K", "--tk", action="store_true",
                 help="include TCL/TK in the deployment")
    g.add_option("-a", "--ascii", action="store_true",
                 help="do NOT include unicode encodings "
                      "(default: included if available)")

    g = parser.add_option_group('How to generate')
    g.add_option("-d", "--debug", action="store_true", default=False,
                 help=("use the debug (verbose) build of the executable for "
                       "packaging. This will make the packaged executable be "
                       "more verbose when run."))
    g.add_option("-s", "--strip", action="store_true",
                 help="strip the exe and shared libs "
                      "(don't try this on Windows)")
    g.add_option("--noupx", action="store_true", default=False,
                 help="do not use UPX even if available (works differently "
                      "between Windows and *nix)")
    #p.add_option("-Y", "--crypt", metavar="FILE",
    #             help="encrypt pyc/pyo files")

    g = parser.add_option_group('Windows and Mac OS X specific options')
    g.add_option("-c", "--console", "--nowindowed", dest="console",
                 action="store_true", default=True,
                 help="use a console subsystem executable (default)")
    g.add_option("-w", "--windowed", "--noconsole", dest="console",
                 action="store_false",
                 help="use a windowed subsystem executable, which on Windows "
                      "does not open the console when the program is launched."
                      'Mandatory whe creating .app bundle on Mac OS X')
    g.add_option("-i", "--icon", dest="icon_file",
                 metavar="FILE.ICO or FILE.EXE,ID or FILE.ICNS",
                 help="If FILE is an .ico file, add the icon to the final "
                      "executable. Otherwise, the syntax 'file.exe,id' to "
                      "extract the icon with the specified id "
                      "from file.exe and add it to the final executable. "
                      "If FILE is an .icns file, add the icon to the final "
                      ".app bundle on Mac OS X (for Mac not yet implemented)")

    g = parser.add_option_group('Windows specific options')
    g.add_option("--version-file",
                 dest="version_file", metavar="FILE",
                 help="add a version resource from FILE to the exe")
    g.add_option("-m", "--manifest", metavar="FILE or XML",
                 help="add manifest FILE or XML to the exe")
    g.add_option("-r", "--resource", default=[], dest="resources",
                 metavar="FILE[,TYPE[,NAME[,LANGUAGE]]]", action="append",
                 help="add/update resource of the given type, name and language "
                      "from FILE to the final executable. FILE can be a "
                      "data file or an exe/dll. For data files, atleast "
                      "TYPE and NAME need to be specified, LANGUAGE defaults "
                      "to 0 or may be specified as wildcard * to update all "
                      "resources of the given TYPE and NAME. For exe/dll "
                      "files, all resources from FILE will be added/updated "
                      "to the final executable if TYPE, NAME and LANGUAGE "
                      "are omitted or specified as wildcard *."
                      "Multiple resources are allowed, using this option "
                      "multiple times.")


def main(scripts, configfilename=None, name=None, tk=0, onefile=0,
         console=True, debug=False, strip=0, noupx=0, comserver=0,
         ascii=0, workdir=None, pathex=[], version_file=None,
         icon_file=None, manifest=None, resources=[], crypt=None,
         hookspath=None, **kwargs):

    try:
        config = eval(open(configfilename, 'rU').read())
    except IOError:
        raise SystemExit("Configfile is missing or unreadable. Please run "
                         "utils/Configure.py before building or use "
                         "pyinstaller.py!")

    if config['pythonVersion'] != sys.version:
        raise SystemExit("The current version of Python is not the same "
                         "with which PyInstaller was configured.\n"
                         "Please re-run utils/Configure.py or use "
                         "pyinstaller.py with this version.")

    if not name:
        name = os.path.splitext(os.path.basename(scripts[0]))[0]

    distdir = "dist"
    builddir = os.path.join('build', 'pyi.' + sys.platform, name)

    pathex = pathex[:]
    if workdir is None:
        workdir = os.getcwd()
        pathex.append(workdir)
    else:
        pathex.append(os.getcwd())
    if workdir == HOMEPATH:
        workdir = os.path.join(HOMEPATH, name)
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    exe_options = ''
    if version_file:
        exe_options = "%s, version='%s'" % (exe_options, quote_win_filepath(version_file))
    if icon_file:
        exe_options = "%s, icon='%s'" % (exe_options, quote_win_filepath(icon_file))
    if manifest:
        if "<" in manifest:
            # Assume XML string
            exe_options = "%s, manifest='%s'" % (exe_options, manifest.replace("'", "\\'"))
        else:
            # Assume filename
            exe_options = "%s, manifest='%s'" % (exe_options, quote_win_filepath(manifest))
    if resources:
        resources = map(quote_win_filepath, resources)
        exe_options = "%s, resources=%s" % (exe_options, repr(resources))
    if not ascii and config['hasUnicode']:
        scripts.insert(0, os.path.join(CONFIGDIR, 'support', 'useUnicode.py'))
    scripts = map(Path, scripts)
    d = {'tktree':'',
         'tkpkg' :'',
         'scripts':scripts,
         'pathex' :pathex,
         'hookspath': hookspath,
         #'exename': '',
         'name': name,
         'distdir': repr(distdir),
         'builddir': repr(builddir),
         'debug': debug,
         'strip': strip,
         'upx' : not noupx,
         'crypt' : repr(crypt),
         'crypted': crypt is not None,
         'console': console or debug,
         'exe_options': exe_options}
    if tk:
        d['tktree'] = "TkTree(),"
        if onefile:
            scripts.insert(0, Path(CONFIGDIR, 'support', 'useTK.py'))
            scripts.insert(0, Path(HOMEPATH, 'support', 'unpackTK.py'))
            scripts.append(Path(HOMEPATH, 'support', 'removeTK.py'))
            d['tkpkg'] = "TkPKG(),"
        else:
            scripts.insert(0, Path(CONFIGDIR, 'support', 'useTK.py'))
    scripts.insert(0, Path(HOMEPATH, 'support', '_mountzlib.py'))

    if is_win or is_cygwin:
        d['exename'] = name+'.exe'
        d['dllname'] = name+'.dll'
    else:
        d['exename'] = name

    # only Windows and Mac OS X distinguish windowed and console apps
    if not is_win and not is_darwin:
        d['console'] = True

    specfnm = os.path.join(workdir, name+'.spec')
    specfile = open(specfnm, 'w')
    if onefile:
        specfile.write(onefiletmplt % d)
        if not console:
            specfile.write(bundleexetmplt % d)
    elif comserver:
        specfile.write(comsrvrtmplt % d)
        if not console:
            specfile.write(bundletmplt % d)
    else:
        specfile.write(onedirtmplt % d)
        if not console:
            specfile.write(bundletmplt % d)
    specfile.close()
    return specfnm

