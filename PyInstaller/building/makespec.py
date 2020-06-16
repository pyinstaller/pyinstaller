#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


"""
Automatically build spec files containing a description of the project
"""

import os
import sys
import argparse

from .. import HOMEPATH, DEFAULT_SPECPATH
from .. import log as logging
from ..compat import expand_path, is_darwin, is_win, open_file
from .templates import onefiletmplt, onedirtmplt, cipher_absent_template, \
    cipher_init_template, bundleexetmplt, bundletmplt

logger = logging.getLogger(__name__)
add_command_sep = os.pathsep

# This list gives valid choices for the ``--debug`` command-line option, except
# for the ``all`` choice.
DEBUG_ARGUMENT_CHOICES = ['imports', 'bootloader', 'noarchive']
# This is the ``all`` choice.
DEBUG_ALL_CHOICE = ['all']


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


def add_data_or_binary(string):
    try:
        src, dest = string.split(add_command_sep)
    except ValueError as e:
        # Split into SRC and DEST failed, wrong syntax
        raise argparse.ArgumentError(
            "Wrong syntax, should be SRC{}DEST".format(add_command_sep)
        ) from e
    if not src or not dest:
        # Syntax was correct, but one or both of SRC and DEST was not given
        raise argparse.ArgumentError("You have to specify both SRC and DEST")
    # Return tuple containing SRC and SRC
    return (src, dest)


def make_variable_path(filename, conversions=path_conversions):
    if not os.path.isabs(filename):
        # os.path.commonpath can not compare relative and absolute
        # paths, and if filename is not absolut, none of the
        # paths in conversions will match anyway.
        return None, filename
    for (from_path, to_name) in conversions:
        assert os.path.abspath(from_path) == from_path, (
            "path '%s' should already be absolute" % from_path)
        try:
            common_path = os.path.commonpath([filename, from_path])
        except ValueError:
            # Per https://docs.python.org/3/library/os.path.html#os.path.commonpath,
            # this raises ValueError in several cases which prevent computing
            # a common path.
            common_path = None
        if common_path == from_path:
            rest = filename[len(from_path):]
            if rest.startswith(('\\', '/')):
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
    g.add_argument('--add-data',
                   action='append', default=[], type=add_data_or_binary,
                   metavar='<SRC;DEST or SRC:DEST>', dest='datas',
                   help='Additional non-binary files or folders to be added '
                        'to the executable. The path separator  is platform '
                        'specific, ``os.pathsep`` (which is ``;`` on Windows '
                        'and ``:`` on most unix systems) is used. This option '
                        'can be used multiple times.')
    g.add_argument('--add-binary',
                   action='append', default=[], type=add_data_or_binary,
                   metavar='<SRC;DEST or SRC:DEST>', dest="binaries",
                   help='Additional binary files to be added to the executable. '
                        'See the ``--add-data`` option for more details. '
                        'This option can be used multiple times.')
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
                   help='Optional module or package (the Python name, '
                   'not the path name) that will be ignored (as though '
                   'it was not found). '
                   'This option can be used multiple times.')
    g.add_argument('--key', dest='key',
                   help='The key used to encrypt Python bytecode.')

    g = parser.add_argument_group('How to generate')
    g.add_argument("-d", "--debug",
                   # If this option is not specified, then its default value is
                   # an empty list (no debug options selected).
                   default=[],
                   # Note that ``nargs`` is omitted. This produces a single item
                   # not stored in a list, as opposed to list containing one
                   # item, per `nargs <https://docs.python.org/3/library/argparse.html#nargs>`_.
                   nargs=None,
                   # The options specified must come from this list.
                   choices=DEBUG_ALL_CHOICE + DEBUG_ARGUMENT_CHOICES,
                   # Append choice, rather than storing them (which would
                   # overwrite any previous selections).
                   action='append',
                   # Allow newlines in the help text; see the
                   # ``_SmartFormatter`` in ``__main__.py``.
                   help=("R|Provide assistance with debugging a frozen\n"
                         "application. This argument may be provided multiple\n"
                         "times to select several of the following options.\n"
                         "\n"
                         "- all: All three of the following options.\n"
                         "\n"
                         "- imports: specify the -v option to the underlying\n"
                         "  Python interpreter, causing it to print a message\n"
                         "  each time a module is initialized, showing the\n"
                         "  place (filename or built-in module) from which it\n"
                         "  is loaded. See\n"
                         "  https://docs.python.org/3/using/cmdline.html#id4.\n"
                         "\n"
                         "- bootloader: tell the bootloader to issue progress\n"
                         "  messages while initializing and starting the\n"
                         "  bundled app. Used to diagnose problems with\n"
                         "  missing imports.\n"
                         "\n"
                         "- noarchive: instead of storing all frozen Python\n"
                         "  source files as an archive inside the resulting\n"
                         "  executable, store them as files in the resulting\n"
                         "  output directory.\n"
                         "\n"))
    g.add_argument("-s", "--strip", action="store_true",
                   help="Apply a symbol-table strip to the executable and shared libs "
                        "(not recommended for Windows)")
    g.add_argument("--noupx", action="store_true", default=False,
                   help="Do not use UPX even if it is available "
                        "(works differently between Windows and *nix)")
    g.add_argument("--upx-exclude", dest="upx_exclude", metavar="FILE",
                   action="append",
                   help="Prevent a binary from being compressed when using "
                        "upx. This is typically used if upx corrupts certain "
                        "binaries during compression. "
                        "FILE is the filename of the binary without path. "
                        "This option can be used multiple times.")

    g = parser.add_argument_group('Windows and Mac OS X specific options')
    g.add_argument("-c", "--console", "--nowindowed", dest="console",
                   action="store_true", default=True,
                   help="Open a console window for standard i/o (default). "
                        "On Windows this option will have no effect if the "
                        "first script is a '.pyw' file.")
    g.add_argument("-w", "--windowed", "--noconsole", dest="console",
                   action="store_false",
                   help="Windows and Mac OS X: do not provide a console window "
                        "for standard i/o. "
                        "On Mac OS X this also triggers building an OS X .app bundle. "
                        "On Windows this option will be set if the first "
                        "script is a '.pyw' file. "
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

    g = parser.add_argument_group('Rarely used special options')
    g.add_argument("--runtime-tmpdir", dest="runtime_tmpdir", metavar="PATH",
                   help="Where to extract libraries and support files in "
                        "`onefile`-mode. "
                        "If this option is given, the bootloader will ignore "
                        "any temp-folder location defined by the run-time OS. "
                        "The ``_MEIxxxxxx``-folder will be created here. "
                        "Please use this option only if you know what you "
                        "are doing.")
    g.add_argument("--bootloader-ignore-signals", action="store_true",
                   default=False,
                   help=("Tell the bootloader to ignore signals rather "
                         "than forwarding them to the child process. "
                         "Useful in situations where e.g. a supervisor "
                         "process signals both the bootloader and child "
                         "(e.g. via a process group) to avoid signalling "
                         "the child twice."))


def main(scripts, name=None, onefile=None,
         console=True, debug=None, strip=False, noupx=False, upx_exclude=None,
         runtime_tmpdir=None, pathex=None, version_file=None, specpath=None,
         bootloader_ignore_signals=False,
         datas=None, binaries=None, icon_file=None, manifest=None, resources=None, bundle_identifier=None,
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
    upx_exclude = upx_exclude or []

    # If file extension of the first script is '.pyw', force --windowed option.
    if is_win and os.path.splitext(scripts[0])[-1] == '.pyw':
        console = False

    # If script paths are relative, make them relative to the directory containing .spec file.
    scripts = [make_path_spec_relative(x, specpath) for x in scripts]
    # With absolute paths replace prefix with variable HOMEPATH.
    scripts = list(map(Path, scripts))

    if key:
        # Tries to import tinyaes since we need it for bytecode obfuscation.
        try:
            import tinyaes  # noqa: F401 (test import)
        except ImportError:
            logger.error('We need tinyaes to use byte-code obfuscation but we '
                         'could not')
            logger.error('find it. You can install it with pip by running:')
            logger.error('  pip install tinyaes')
            sys.exit(1)
        cipher_init = cipher_init_template % {'key': key}
    else:
        cipher_init = cipher_absent_template

    # Translate the default of ``debug=None`` to an empty list.
    if debug is None:
        debug = []
    # Translate the ``all`` option.
    if DEBUG_ALL_CHOICE[0] in debug:
        debug = DEBUG_ARGUMENT_CHOICES

    d = {
        'scripts': scripts,
        'pathex': pathex,
        'binaries': binaries,
        'datas': datas,
        'hiddenimports': hiddenimports,
        'name': name,
        'noarchive': 'noarchive' in debug,
        'options': [('v', None, 'OPTION')] if 'imports' in debug else [],
        'debug_bootloader': 'bootloader' in debug,
        'bootloader_ignore_signals': bootloader_ignore_signals,
        'strip': strip,
        'upx': not noupx,
        'upx_exclude': upx_exclude,
        'runtime_tmpdir': runtime_tmpdir,
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
    with open_file(specfnm, 'w', encoding='utf-8') as specfile:
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

    return specfnm
