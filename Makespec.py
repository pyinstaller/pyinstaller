#! /usr/bin/env/python

import sys, os, string

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
        if filename.startswith(from_path):
            rest = filename[len(from_path):]
            if rest[0] in "\\/": 
                rest = rest[1:]
            return to_name, rest
    return None, filename
        
# An object used in place of a "path string" which knows how to repr()
# itself using variable names instead of hard-coded paths.
class Path:
    def __init__(self, *parts):
        self.path = os.path.join(*parts)
        self.variable_prefix = self.filename_suffix = None
    def __repr__(self):
        if self.filename_suffix is None:
            self.variable_prefix, self.filename_suffix = make_variable_path(self.path)
        if self.variable_prefix is None:
            return repr(self.path)
        return "os.path.join(" + self.variable_prefix + "," + repr(self.filename_suffix) + ")"
        
def main(scripts, name=None, tk=0, freeze=0, console=1, debug=0, strip=0, upx=0,
         comserver=0, ascii=0, workdir=None, pathex=None, version_file=None, icon_file=None):
    if name is None:
        name = os.path.splitext(os.path.basename(scripts[0]))[0]
    distdir = "dist%s" % name
    builddir = "build%s" % name
    if pathex is None:
        pathex = []
    elif type(pathex) is type(''):
        if iswin:
            pathex = string.split(pathex, ';')
        else:
            pathex = string.split(pathex, ':')
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
        scripts[i] = Path(scripts[i])
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

usage = """\
Usage: python %s [options] <scriptname> [<scriptname> ...]
 --onefile -> create a single file deployment
 --onedir  -> create a single directory deployment (default)
 --tk -> include TCL/TK in the deployment
 --noconsole -> use a Windows subsystem executable (Windows only)
 --ascii -> do NOT include unicode encodings (default: included if available)
 --debug -> use the debug (verbose) build of the executable
 --strip -> strip the exe and shared libs (don't try this on Windows)
 --upx -> use UPX if available (works differently Windows / Linux)
 --out dir -> gemerate the spec file in dir
 --paths pathstring -> like using PYTHONPATH
 --icon file.ico -> add the icon in file.ico to the exe (Windows only)
 --icon file.exe,id -> add the icon with id from file.exe to the exe (Windows only)
 --version verfile -> add a version resource from verfile to the exe (Windows only)
The next step is to run Build.py against the generated spec file.
See doc/begin.html for details.
"""

#scripts, name=None, tk=0, freeze=0, console=1, debug=0,workdir=None, pathex=None
if __name__ == '__main__':
    import getopt
    tk = freeze = debug = ascii = strip = upx = 0
    console = 1
    workdir = name = pathex = None
    icon_file = None
    version_file = None
    opts, args = getopt.getopt(sys.argv[1:], '',
            ['onefile', 'onedir', 'tk', 'noconsole', 'debug', 'ascii',
             'strip', 'upx', 'out=', 'name=', 'paths=', 'version=', 'icon='])
    for opt, val in opts:
        if opt == '--onefile':
            freeze = 1
        elif opt == '--onedir':
            freeze = 0
        elif opt == '--tk':
            tk = 1
        elif opt == '--noconsole':
            console = 0
        elif opt == '--debug':
            debug = 1
        elif opt == '--out':
            workdir = val
        elif opt == '--name':
            name = val
        elif opt == '--ascii':
            ascii = 1
        elif opt == '--strip':
            strip = 1
        elif opt == '--upx':
            upx = 1
        elif opt == '--icon':
            icon_file = val
        elif opt == '--version':
            version_file = val
        elif opt == '--paths':
            pathex = val
        else:
            print "bad option: %s" % (opt, val)
            print usage % sys.argv[0]
            sys.exit(1)
    if not args:
        print usage % sys.argv[0]
    else:
        nm = main(args, name=name, tk=tk, freeze=freeze, console=console,
                  debug=debug, strip=strip, upx=upx, ascii=ascii,
                  workdir=workdir, pathex=pathex,
                  version_file=version_file, icon_file=icon_file)
        print "wrote %s" % nm

