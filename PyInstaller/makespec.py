#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
Automatically build spec files containing a description of the project
"""


import os


from PyInstaller import HOMEPATH, DEFAULT_SPECPATH
from PyInstaller.compat import expand_path, is_win, is_cygwin, is_darwin


onefiletmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             hiddenimports=%(hiddenimports)r,
             hookspath=%(hookspath)r,
             runtime_hooks=%(runtime_hooks)r)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='%(exename)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
"""

onedirtmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             hiddenimports=%(hiddenimports)r,
             hookspath=%(hookspath)r,
             runtime_hooks=%(runtime_hooks)r)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='%(exename)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=%(strip)s,
               upx=%(upx)s,
               name='%(name)s')
"""

comsrvrtmplt = """# -*- mode: python -*-
a = Analysis(%(scripts)s,
             pathex=%(pathex)s,
             hiddenimports=%(hiddenimports)r,
             hookspath=%(hookspath)r,
             runtime_hooks=%(runtime_hooks)r)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='%(exename)s',
          debug=%(debug)s,
          strip=%(strip)s,
          upx=%(upx)s,
          console=%(console)s %(exe_options)s)
dll = DLL(pyz,
          a.scripts,
          exclude_binaries=True,
          name='%(dllname)s',
          debug=%(debug)s)
coll = COLLECT(exe, dll,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=%(strip)s,
               upx=%(upx)s,
               name='%(name)s')
"""

bundleexetmplt = """app = BUNDLE(exe,
             name='%(exename)s.app',
             icon=%(icon)s)
"""

bundletmplt = """app = BUNDLE(coll,
             name='%(name)s.app',
             icon=%(icon)s)
"""


def quote_win_filepath(path):
    # quote all \ with another \ after using normpath to clean up the path
    return os.path.normpath(path).replace('\\', '\\\\')


# Support for trying to avoid hard-coded paths in the .spec files.
# Eg, all files rooted in the Installer directory tree will be
# written using "HOMEPATH", thus allowing this spec file to
# be used with any Installer installation.
# Same thing could be done for other paths too.
path_conversions = (
    (HOMEPATH, "HOMEPATH"),
    )


def make_variable_path(filename, conversions=path_conversions):
    for (from_path, to_name) in conversions:
        assert os.path.abspath(from_path) == from_path, (
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
                 help="Create a one-file bundled executable.")
    g.add_option("-D", "--onedir", dest="onefile",
                 action="store_false",
                 help="Create a one-folder bundle containing an executable (default)")
    g.add_option("--specpath", metavar="DIR", default=None,
                 help="Folder to store the generated spec file "
                      "(default: current directory)")
    g.add_option("-n", "--name",
                 help="Name to assign to the bundled app and spec file "
                      "(default: first script's basename)")

    g = parser.add_option_group('What to bundle, where to search')
    g.add_option("-p", "--paths", default=[], dest="pathex",
                 metavar="DIR", action="append",
                 help="A path to search for imports (like using PYTHONPATH). "
                      "Multiple paths are allowed, separated "
                      "by %s, or use this option multiple times"
                      % repr(os.pathsep))
    g.add_option('--hidden-import',
                 action='append',
                 metavar="MODULENAME", dest='hiddenimports',
                 help='Name an import not visible in the code of the script(s). '
                 'This option can be used multiple times.')
    g.add_option("--additional-hooks-dir", action="append", dest="hookspath",
                 help="An additional path to search for hooks. "
                      "This option can be used multiple times.")
    g.add_option('--runtime-hook', action='append', dest='runtime_hooks',
            help='Path to a custom runtime hook file. A runtime hook '
            'is code that is bundled with the executable and '
            'is executed before any other code or module '
            'to set up special features of the runtime environment. '
            'This option can be used multiple times.')

    g = parser.add_option_group('How to generate')
    g.add_option("-d", "--debug", action="store_true", default=False,
                 help=("Tell the bootloader to issue progress messages "
                       "while initializing and starting the bundled app. "
                       "Used to diagnose problems with missing imports."))
    g.add_option("-s", "--strip", action="store_true",
                 help="Apply a symbol-table strip to the executable and shared libs "
                      "(not recommended for Windows)")
    g.add_option("--noupx", action="store_true", default=False,
                 help="Do not use UPX even if it is available "
                      "(works differently between Windows and *nix)")

    g = parser.add_option_group('Windows and Mac OS X specific options')
    g.add_option("-c", "--console", "--nowindowed", dest="console",
                 action="store_true", default=True,
                 help="Open a console window for standard i/o (default)")
    g.add_option("-w", "--windowed", "--noconsole", dest="console",
                 action="store_false",
                 help="Windows and Mac OS X: do not provide a console window "
                      "for standard i/o. "
                      "On Mac OS X this also triggers building an OS X .app bundle."
                      "This option is ignored in *NIX systems.")
    g.add_option("-i", "--icon", dest="icon_file",
                 metavar="FILE.ico or FILE.exe,ID or FILE.icns",
                 help="FILE.ico: apply that icon to a Windows executable. "
                      "FILE.exe,ID, extract the icon with ID from an exe. "
                      "FILE.icns: apply the icon to the "
                      ".app bundle on Mac OS X")

    g = parser.add_option_group('Windows specific options')
    g.add_option("--version-file",
                 dest="version_file", metavar="FILE",
                 help="add a version resource from FILE to the exe")
    g.add_option("-m", "--manifest", metavar="FILE or XML",
                 help="add manifest FILE or XML to the exe")
    g.add_option("-r", "--resource", default=[], dest="resources",
                 metavar="FILE[,TYPE[,NAME[,LANGUAGE]]]", action="append",
                 help="Add or update a resource of the given type, name and language "
                      "from FILE to a Windows executable. FILE can be a "
                      "data file or an exe/dll. For data files, at least "
                      "TYPE and NAME must be specified. LANGUAGE defaults "
                      "to 0 or may be specified as wildcard * to update all "
                      "resources of the given TYPE and NAME. For exe/dll "
                      "files, all resources from FILE will be added/updated "
                      "to the final executable if TYPE, NAME and LANGUAGE "
                      "are omitted or specified as wildcard *."
                      "This option can be used multiple times.")


def main(scripts, name=None, onefile=False,
         console=True, debug=False, strip=False, noupx=False, comserver=False,
         pathex=[], version_file=None, specpath=DEFAULT_SPECPATH,
         icon_file=None, manifest=None, resources=[],
         hiddenimports=None, hookspath=None, runtime_hooks=[], **kwargs):

    # If appname is not specified - use the basename of the main script as name.
    if name is None:
        name = os.path.splitext(os.path.basename(scripts[0]))[0]

    # If specpath not specified - use default value - current working directory.
    if specpath is None:
        specpath = DEFAULT_SPECPATH
    else:
        # Expand tilde to user's home directory.
        specpath = expand_path(specpath)
    # If cwd is the root directory of PyInstaller then generate .spec file
    # subdirectory ./appname/.
    if specpath == HOMEPATH:
        specpath = os.path.join(HOMEPATH, name)
    # Create directory tree if missing.
    if not os.path.exists(specpath):
        os.makedirs(specpath)

    # Append specpath to PYTHONPATH - where to look for additional Python modules.
    pathex = pathex[:]
    pathex.append(specpath)

    exe_options = ''
    if version_file:
        exe_options = "%s, version='%s'" % (exe_options, quote_win_filepath(version_file))

    if icon_file:
        # Icon file for Windows.
        # On Windows default icon is embedded in the bootloader executable.
        exe_options = "%s, icon='%s'" % (exe_options, quote_win_filepath(icon_file))
        # Icon file for OSX.
        # We need to encapsulate it into apostrofes.
        icon_file = "'%s'" % icon_file
    else:
        # On OSX default icon has to be copied into the .app bundle.
        # The the text value 'None' means - use default icon.
        icon_file = 'None'

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

    hiddenimports = hiddenimports or []
    scripts = map(Path, scripts)

    d = {'scripts': scripts,
        'pathex': pathex,
        'hiddenimports': hiddenimports,
        'name': name,
        'debug': debug,
        'strip': strip,
        'upx': not noupx,
        'exe_options': exe_options,
        # Directory with additional custom import hooks.
        'hookspath': hookspath,
        # List with custom runtime hook files.
        'runtime_hooks': runtime_hooks,
        # only Windows and Mac OS X distinguish windowed and console apps
        'console': console,
        # Icon filename. Only OSX uses this item.
        'icon': icon_file,
    }

    if is_win or is_cygwin:
        d['exename'] = name + '.exe'
        d['dllname'] = name + '.dll'
    else:
        d['exename'] = name

    # Write down .spec file to filesystem.
    specfnm = os.path.join(specpath, name + '.spec')
    specfile = open(specfnm, 'w')
    if comserver:
        specfile.write(comsrvrtmplt % d)
    elif onefile:
        specfile.write(onefiletmplt % d)
        # For OSX create .app bundle.
        if is_darwin and not console:
            specfile.write(bundleexetmplt % d)
    else:
        specfile.write(onedirtmplt % d)
        # For OSX create .app bundle.
        if is_darwin and not console:
            specfile.write(bundletmplt % d)
    specfile.close()

    return specfnm
