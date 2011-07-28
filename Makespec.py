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

import sys, os, string

# For Python 1.5 compatibility
try:
    True, False
except:
    True  = 1 == 1
    False = not True

freezetmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s)
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

collecttmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s)
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
             pathex=%(pathex)s)
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

HOME = os.path.dirname(sys.argv[0])
HOME = os.path.abspath(HOME)

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


def main(scripts, configfile=None, name=None, tk=0, freeze=0, console=1, debug=0,
         strip=0, upx=0, comserver=0, ascii=0, workdir=None,
         pathex=[], version_file=None, icon_file=None, manifest=None, resources=[], crypt=None, **kwargs):

    try:
        config = eval(open(configfile, 'r').read())
    except IOError:
        raise SystemExit("Configfile is missing or unreadable. Please run Configure.py before building!")

    if config['pythonVersion'] != sys.version:
        print "The current version of Python is not the same with which PyInstaller was configured."
        print "Please re-run Configure.py with this version."
        raise SystemExit(1)

    if not name:
        name = os.path.splitext(os.path.basename(scripts[0]))[0]

    distdir = "dist"
    builddir = os.path.join('build', 'pyi.' + config['target_platform'], name)

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
    if manifest:
        if "<" in manifest:
            # Assume XML string
            exe_options = "%s, manifest='%s'" % (exe_options, manifest.replace("'", "\\'"))
        else:
            # Assume filename
            exe_options = "%s, manifest='%s'" % (exe_options, quote_win_filepath(manifest))
    if resources:
        for i in range(len(resources)):
            resources[i] = quote_win_filepath(resources[i])
        exe_options = "%s, resources=%s" % (exe_options, repr(resources))
    if not ascii and config['hasUnicode']:
        scripts.insert(0, os.path.join(HOME, 'support', 'useUnicode.py'))
    for i in range(len(scripts)):
        scripts[i] = Path(scripts[i]) # Use relative path in specfiles

    d = {'tktree':'',
         'tkpkg' :'',
         'scripts':scripts,
         'pathex' :pathex,
         #'exename': '',
         'name': name,
         'distdir': repr(distdir),
         'builddir': repr(builddir),
         'debug': debug,
         'strip': strip,
         'upx' : upx,
         'crypt' : repr(crypt),
         'crypted': crypt is not None,
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
    if config['target_platform'][:3] == "win" or \
       config['target_platform'] == 'cygwin':
        d['exename'] = name+'.exe'
        d['dllname'] = name+'.dll'
    else:
        d['exename'] = name

    # only Windows and Mac OS X distinguish windowed and console apps
    if not config['target_platform'][:3] == "win" and \
       not config['target_platform'].startswith('darwin'):
        d['console'] = 1

    specfnm = os.path.join(workdir, name+'.spec')
    specfile = open(specfnm, 'w')
    if freeze:
        specfile.write(freezetmplt % d)
        if not console:
            specfile.write(bundleexetmplt % d)
    elif comserver:
        specfile.write(comsrvrtmplt % d)
        if not console:
            specfile.write(bundletmplt % d)
    else:
        specfile.write(collecttmplt % d)
        if not console:
            specfile.write(bundletmplt % d)
    specfile.close()
    return specfnm


if __name__ == '__main__':
    import pyi_optparse as optparse
    p = optparse.OptionParser(
        usage="python %prog [opts] <scriptname> [<scriptname> ...]"
    )
    p.add_option('-C', '--configfile',
                 default=os.path.join(HOME, 'config.dat'),
                 help='Name of configfile (default: %default)')

    g = p.add_option_group('What to generate')
    g.add_option("-F", "--onefile", dest="freeze",
                 action="store_true", default=False,
                 help="create a single file deployment")
    g.add_option("-D", "--onedir", dest="freeze", action="store_false",
                 help="create a single directory deployment (default)")
    g.add_option("-o", "--out", type="string", default=None,
                 dest="workdir", metavar="DIR",
                 help="generate the spec file in the specified directory "
                      "(default: current directory")
    g.add_option("-n", "--name", type="string", default=None,
                 metavar="NAME",
                 help="name to assign to the project "
                      "(default: first script's basename)")

    g = p.add_option_group('What to bundle, where to search')
    g.add_option("-p", "--paths", type="string", default=[], dest="pathex",
                 metavar="DIR", action="append",
                 help="set base path for import (like using PYTHONPATH). "
                      "Multiple directories are allowed, separating them "
                      "with %s, or using this option multiple times"
                      % repr(os.pathsep))
    g.add_option("-K", "--tk", default=False, action="store_true",
                 help="include TCL/TK in the deployment")
    g.add_option("-a", "--ascii", action="store_true", default=False,
                 help="do NOT include unicode encodings "
                      "(default: included if available)")

    g = p.add_option_group('How to generate')
    g.add_option("-d", "--debug", action="store_true", default=False,
                 help="use the debug (verbose) build of the executable")
    g.add_option("-s", "--strip", action="store_true", default=False,
                 help="strip the exe and shared libs "
                      "(don't try this on Windows)")
    g.add_option("-X", "--upx", action="store_true", default=True,
                 help="use UPX if available (works differently between "
                      "Windows and *nix)")
    #p.add_option("-Y", "--crypt", type="string", default=None, metavar="FILE",
    #             help="encrypt pyc/pyo files")

    g = p.add_option_group('Windows and Mac OS X specific options')
    g.add_option("-c", "--console", "--nowindowed", dest="console",
                 action="store_true",
                 help="use a console subsystem executable"
                      "(default)")
    g.add_option("-w", "--windowed", "--noconsole", dest="console",
                 action="store_false", default=True,
                 help="use a Windows subsystem executable")

    g = p.add_option_group('Windows specific options')
    g.add_option("-v", "--version", type="string",
                 dest="version_file", metavar="FILE",
                 help="add a version resource from FILE to the exe ")
    g.add_option("-i", "--icon", type="string", dest="icon_file",
                 metavar="FILE.ICO or FILE.EXE,ID",
                 help="If FILE is an .ico file, add the icon to the final "
                      "executable. Otherwise, the syntax 'file.exe,id' to "
                      "extract the icon with the specified id "
                      "from file.exe and add it to the final executable")
    g.add_option("-m", "--manifest", type="string",
                 dest="manifest", metavar="FILE or XML",
                 help="add manifest FILE or XML to the exe ")
    g.add_option("-r", "--resource", type="string", default=[], dest="resources",
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

    opts,args = p.parse_args()

    # Split pathex by using the path separator
    temppaths = opts.pathex[:]
    opts.pathex = []
    for p in temppaths:
        opts.pathex.extend(string.split(p, os.pathsep))

    if not args:
        p.error('Requires at least one scriptname file')

    name = apply(main, (args,), opts.__dict__)
    print "wrote %s" % name
    print "now run Build.py to build the executable"
