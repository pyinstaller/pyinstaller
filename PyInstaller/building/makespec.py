#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
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
import sys

from .. import HOMEPATH, DEFAULT_SPECPATH
from .. import log as logging
from ..compat import expand_path, is_win, is_cygwin, is_darwin
from .templates import onefiletmplt, onedirtmplt, cipher_absent_template, \
    cipher_init_template, bundleexetmplt, bundletmplt

logger = logging.getLogger(__name__)


def quote_win_filepath(path):
    # quote all \ with another \ after using normpath to clean up the path
    return os.path.normpath(path).replace('\\', '\\\\')


def make_path_spec_relative(filename, spec_dir):
    """
    Make the filename relative to the directory containing .spec file if filename
    is relative and not absolute. Otherwise keep filename untouched.
    """
    if os.path.isabs(filename):
        return filename
    else:
        filename = os.path.abspath(filename)
        # Make it relative.
        filename = os.path.relpath(filename, start=spec_dir)
        return filename


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
        self.path = os.path.join(*parts)
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
    g = parser.add_argument_group('What to generate')
    g.add_argument("-D", "--onedir", dest="onefile",
                   action="store_false", default=False,
                   help="Create a one-folder bundle containing an executable (default)")
    g.add_argument("-F", "--onefile", dest="onefile",
                   action="store_true", default=False,
                   help="Create a one-file bundled executable.")
    g.add_argument("--specpath", metavar="DIR",
                   help="Folder to store the generated spec file "
                        "(default: current directory)")
    g.add_argument("-n", "--name",
                   help="Name to assign to the bundled app and spec file "
                        "(default: first script's basename)")

    g = parser.add_argument_group('What to bundle, where to search')
    g.add_argument("-p", "--paths", dest="pathex",
                   metavar="DIR", action="append", default=[],
                   help="A path to search for imports (like using PYTHONPATH). "
                        "Multiple paths are allowed, separated "
                        "by %s, or use this option multiple times"
                        % repr(os.pathsep))
    g.add_argument('--hidden-import', '--hiddenimport',
                   action='append', default=[],
                   metavar="MODULENAME", dest='hiddenimports',
                   help='Name an import not visible in the code of the script(s). '
                   'This option can be used multiple times.')
    g.add_argument("--additional-hooks-dir", action="append", dest="hookspath",
                   default=[],
                   help="An additional path to search for hooks. "
                        "This option can be used multiple times.")
    g.add_argument('--runtime-hook', action='append', dest='runtime_hooks',
                   default=[],
                   help='Path to a custom runtime hook file. A runtime hook '
                   'is code that is bundled with the executable and '
                   'is executed before any other code or module '
                   'to set up special features of the runtime environment. '
                   'This option can be used multiple times.')
    g.add_argument('--exclude-module', dest='excludes', action='append',
                   default=[],
                   help='Optional module or package (his Python names, '
                   'not path names) that will be ignored (as though '
                   'it was not found). '
                   'This option can be used multiple times.')
    g.add_argument('--key', dest='key',
                   help='The key used to encrypt Python bytecode.')

    g = parser.add_argument_group('How to generate')
    g.add_argument("-d", "--debug", action="store_true", default=False,
                   help=("Tell the bootloader to issue progress messages "
                         "while initializing and starting the bundled app. "
                         "Used to diagnose problems with missing imports."))
    g.add_argument("-s", "--strip", action="store_true",
                   help="Apply a symbol-table strip to the executable and shared libs "
                        "(not recommended for Windows)")
    g.add_argument("--noupx", action="store_true", default=False,
                   help="Do not use UPX even if it is available "
                        "(works differently between Windows and *nix)")

    g = parser.add_argument_group('Windows and Mac OS X specific options')
    g.add_argument("-c", "--console", "--nowindowed", dest="console",
                   action="store_true", default=True,
                   help="Open a console window for standard i/o (default)")
    g.add_argument("-w", "--windowed", "--noconsole", dest="console",
                   action="store_false",
                   help="Windows and Mac OS X: do not provide a console window "
                        "for standard i/o. "
                        "On Mac OS X this also triggers building an OS X .app bundle. "
                        "This option is ignored in *NIX systems.")
    g.add_argument("-i", "--icon", dest="icon_file",
                   metavar="<FILE.ico or FILE.exe,ID or FILE.icns>",
                   help="FILE.ico: apply that icon to a Windows executable. "
                        "FILE.exe,ID, extract the icon with ID from an exe. "
                        "FILE.icns: apply the icon to the "
                        ".app bundle on Mac OS X")

    g = parser.add_argument_group('Windows specific options')
    g.add_argument("--version-file",
                   dest="version_file", metavar="FILE",
                   help="add a version resource from FILE to the exe")
    g.add_argument("-m", "--manifest", metavar="<FILE or XML>",
                   help="add manifest FILE or XML to the exe")
    g.add_argument("-r", "--resource", dest="resources",
                   metavar="RESOURCE", action="append",
                   default=[],
                   help="Add or update a resource to a Windows executable. "
                        "The RESOURCE is one to four items, "
                        "FILE[,TYPE[,NAME[,LANGUAGE]]]. "
                        "FILE can be a "
                        "data file or an exe/dll. For data files, at least "
                        "TYPE and NAME must be specified. LANGUAGE defaults "
                        "to 0 or may be specified as wildcard * to update all "
                        "resources of the given TYPE and NAME. For exe/dll "
                        "files, all resources from FILE will be added/updated "
                        "to the final executable if TYPE, NAME and LANGUAGE "
                        "are omitted or specified as wildcard *."
                        "This option can be used multiple times.")
    g.add_argument('--uac-admin', dest='uac_admin', action="store_true", default=False,
                   help='Using this option creates a Manifest '
                        'which will request elevation upon application restart.')
    g.add_argument('--uac-uiaccess', dest='uac_uiaccess', action="store_true", default=False,
                   help='Using this option allows an elevated application to '
                        'work with Remote Desktop.')

    g = parser.add_argument_group('Windows Side-by-side Assembly searching options (advanced)')
    g.add_argument("--win-private-assemblies", dest="win_private_assemblies",
                   action="store_true",
                   help="Any Shared Assemblies bundled into the application "
                        "will be changed into Private Assemblies. This means "
                        "the exact versions of these assemblies will always "
                        "be used, and any newer versions installed on user "
                        "machines at the system level will be ignored.")
    g.add_argument("--win-no-prefer-redirects", dest="win_no_prefer_redirects",
                   action="store_true",
                   help="While searching for Shared or Private Assemblies to "
                        "bundle into the application, PyInstaller will prefer "
                        "not to follow policies that redirect to newer versions, "
                        "and will try to bundle the exact versions of the assembly.")


    g = parser.add_argument_group('Mac OS X specific options')
    g.add_argument('--osx-bundle-identifier', dest='bundle_identifier',
                   help='Mac OS X .app bundle identifier is used as the default unique program '
                        'name for code signing purposes. The usual form is a hierarchical name '
                        'in reverse DNS notation. For example: com.mycompany.department.appname '
                        "(default: first script's basename)")


def main(scripts, name=None, onefile=None,
         console=True, debug=False, strip=False, noupx=False,
         pathex=None, version_file=None, specpath=None,
         icon_file=None, manifest=None, resources=None, bundle_identifier=None,
         hiddenimports=None, hookspath=None, key=None, runtime_hooks=None,
         excludes=None, uac_admin=False, uac_uiaccess=False,
         win_no_prefer_redirects=False, win_private_assemblies=False,
         **kwargs):
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
    pathex = pathex or []
    pathex = pathex[:]
    pathex.append(specpath)

    # Handle additional EXE options.
    exe_options = ''
    if version_file:
        exe_options = "%s, version='%s'" % (exe_options, quote_win_filepath(version_file))
    if uac_admin:
        exe_options = "%s, uac_admin=%s" % (exe_options, 'True')
    if uac_uiaccess:
        exe_options = "%s, uac_uiaccess=%s" % (exe_options, 'True')
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

    if bundle_identifier:
        # We need to encapsulate it into apostrofes.
        bundle_identifier = "'%s'" % bundle_identifier

    if manifest:
        if "<" in manifest:
            # Assume XML string
            exe_options = "%s, manifest='%s'" % (exe_options, manifest.replace("'", "\\'"))
        else:
            # Assume filename
            exe_options = "%s, manifest='%s'" % (exe_options, quote_win_filepath(manifest))
    if resources:
        resources = list(map(quote_win_filepath, resources))
        exe_options = "%s, resources=%s" % (exe_options, repr(resources))

    hiddenimports = hiddenimports or []

    # If script paths are relative, make them relative to the directory containing .spec file.
    scripts = [make_path_spec_relative(x, specpath) for x in scripts]
    # With absolute paths replace prefix with variable HOMEPATH.
    scripts = list(map(Path, scripts))

    if key:
        # Tries to import PyCrypto since we need it for bytecode obfuscation. Also make sure its
        # version is >= 2.4.
        try:
            import Crypto

            pycrypto_version = list(map(int, Crypto.__version__.split('.')))
            is_version_acceptable = pycrypto_version[0] >= 2 and pycrypto_version[1] >= 4

            if not is_version_acceptable:
                logger.error('PyCrypto version must be >= 2.4, older versions are not supported.')

                sys.exit(1)
        except ImportError:
            logger.error('We need PyCrypto >= 2.4 to use byte-code obufscation but we could not')
            logger.error('find it. You can install it with pip by running:')
            logger.error('  pip install PyCrypto')

            sys.exit(1)

        cipher_init = cipher_init_template % {'key': key}
    else:
        cipher_init = cipher_absent_template

    d = {
        'scripts': scripts,
        'pathex': pathex,
        'hiddenimports': hiddenimports,
        'name': name,
        'debug': debug,
        'strip': strip,
        'upx': not noupx,
        'exe_options': exe_options,
        'cipher_init': cipher_init,
        # Directory with additional custom import hooks.
        'hookspath': hookspath,
        # List with custom runtime hook files.
        'runtime_hooks': runtime_hooks or [],
        # List of modules/pakages to ignore.
        'excludes': excludes or [],
        # only Windows and Mac OS X distinguish windowed and console apps
        'console': console,
        # Icon filename. Only OSX uses this item.
        'icon': icon_file,
        # .app bundle identifier. Only OSX uses this item.
        'bundle_identifier': bundle_identifier,
        # Windows assembly searching options
        'win_no_prefer_redirects': win_no_prefer_redirects,
        'win_private_assemblies': win_private_assemblies,
    }

    # Write down .spec file to filesystem.
    specfnm = os.path.join(specpath, name + '.spec')
    specfile = open(specfnm, 'w')
    if onefile:
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
