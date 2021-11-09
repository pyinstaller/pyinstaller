# -----------------------------------------------------------------------------
# Copyright (c) 2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------
import os

import click
from click_option_group import optgroup

from PyInstaller import DEFAULT_DISTPATH, DEFAULT_WORKPATH


def is_ident(value: str) -> bool:
    if all(x.isidentifier() for x in value.split('.')):
        return True
    raise click.BadParameter(f'{value} is not a valid identifier')


def add_build_options(cmd: click.Command) -> click.Command:
    """
    Decorator which adds all build-arguments to a click command
    """
    cmd = optgroup.option(
        '-y/-N',
        '--noconfirm/--confirm',
        is_flag=True,
        default=True,
        help='Replace output directory without asking for confirmation'
    )(cmd)
    cmd = optgroup.option(
        '--upx-dir', default=None, type=click.Path(), help='Path to UPX utility (default: search PATH)'
    )(cmd)
    cmd = optgroup.option(
        '--workpath',
        default=DEFAULT_WORKPATH,
        type=click.Path(),
        help='Where to put all the temporary work files - .log, .pyz, etc. (default: ./build)'
    )(cmd)
    cmd = optgroup.option(
        '--distpath',
        default=DEFAULT_DISTPATH,
        type=click.Path(),
        help='Where to put the bundled app (default: ./dist)'
    )(cmd)
    cmd = optgroup.option(
        '--clean',
        is_flag=True,
        default=False,
        help='Clean PyInstaller cache and remove temporary files before building'
    )(cmd)
    cmd = optgroup.option(
        '-a',
        '--ascii',
        is_flag=True,
        default=False,
        help='Don\'t include unicode support (default: included if available)'
    )(cmd)
    cmd = optgroup('Output Options')(cmd)

    return cmd


def add_logging_options(cmd: click.Command) -> click.Command:
    levels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL')

    cmd = optgroup.option(
        '--log-level',
        type=click.Choice(levels, case_sensitive=False),
        help='Amount of detail in build-time logging output.'
    )(cmd)
    cmd = optgroup('Logging')(cmd)

    return cmd


def add_makespec_options(cmd: click.Command) -> click.Command:

    # Group: Rarely used special options

    cmd = optgroup.option(
        '--python-option',
        'python_option',
        multiple=True,
        metavar='PYTHON_OPTION',
        help='Specify a command-line option to pass to the python interpreter at runtime. '
        'Currently supports "v" (equivalent to ``-d imports``), "u", and "W <warning control>".'
    )(cmd)
    cmd = optgroup.option(
        '--runtime-tempdir',
        metavar='PATH',
        help='Where to extract libraries and support files in `onefile`-mode. If this option is given, the '
        'bootloader will ignore any temp-folder location defined by the run-time OS. The '
        '``_MEIxxxxxx``-folder will be created here. Please use this option only if you know what '
        'you are doing.',
    )(cmd)
    cmd = optgroup.option(
        '--bootloader-ignore-signals',
        is_flag=True,
        default=False,
        help='Tell the bootloader to ignore signals rather than forwarding them to the child process. '
        'Useful in situations where for example a supervisor process signals both the bootloader '
        'and the child (e.g., via a process group) to avoid signalling the child twice.',
    )(cmd)
    cmd = optgroup('Rarely used special options')(cmd)

    # Group: macOS specific options

    cmd = optgroup.option(
        '--argv-emulation',
        is_flag=True,
        default=False,
        help='Enable argv emulation for macOS app bundles. If enabled, the initial open document/URL '
        'event is processed by the bootloader and the passed file paths or URLs are appended '
        'to sys.argv.',
    )(cmd)
    cmd = optgroup.option(
        '--osx-bundle-identifier',
        'bundle_identifier',
        type=str,
        help='Mac OS .app bundle identifier is used as the default unique program name for code signing '
        'purposes. The usual form is a hierarchical name in reverse DNS notation. For example: '
        'com.mycompany.department.appname (default: first script\'s basename)'
    )(cmd)
    cmd = optgroup.option(
        '--target-arch',
        'target_arch',
        metavar='ARCH',
        help='Target architecture (macOS only; valid values: x86_64, arm64, universal2). Enables switching '
        'between universal2 and single-arch version of frozen application (provided python '
        'installation supports the target architecture). If not target architecture is not specified, '
        'the current running architecture is targeted.',
    )(cmd)
    cmd = optgroup.option(
        '--codesign-identity',
        metavar='IDENTITY',
        help='Code signing identity (macOS only). Use the provided identity to sign collected binaries and '
        'generated executable. If signing identity is not provided, ad-hoc signing is performed instead.',
    )(cmd)
    cmd = optgroup.option(
        '--osx-entitlements-files',
        'entitlements_file',
        metavar='FILE',
        help='Entitlements file to use when code-signing the collected binaries (macOS only).',
    )(cmd)
    cmd = optgroup('macOS specific options')(cmd)

    # Group: Windows side-by-side assembly searching options

    cmd = optgroup.option(
        '--win-private-assemblies',
        is_flag=True,
        default=False,
        help='Any Shared Assemblies bundled into the application will be changed into Private Assemblies. '
        'This means the exact versions of these assemblies will always be used, and any newer '
        'versions installed on user machines at the system level will be ignored.'
    )(cmd)
    cmd = optgroup.option(
        '--win-no-prefer-redirects',
        is_flag=True,
        default=False,
        help='While searching for Shared or Private Assemblies to bundle into the application, '
        'PyInstaller will prefer not to follow policies that redirect to newer versions, '
        'and will try to bundle the exact versions of the assembly.'
    )(cmd)
    cmd = optgroup('Windows side-by-side assembly searching options')(cmd)

    # Windows specific options

    cmd = optgroup.option(
        '--version-file',
        'version_file',
        type=click.Path(exists=True, dir_okay=False),
        help='Add a version resource from FILE to the exe.'
    )(cmd)
    cmd = optgroup.option('-m', '--manifest', metavar='<FILE or XML>', help='Add manifest FILE or XML to the exe')(cmd)
    cmd = optgroup.option(
        '--no-embed-manifest',
        'embed_manifest',
        default=True,
        is_flag=True,
        help='Generate an external .exe.manifest instead of embedding the manifest directly into the executable. '
        'This option is ignored in onefile mode.'
    )(cmd)
    cmd = optgroup.option(
        '-r',
        '--resource',
        'resources',
        metavar='FILE',
        multiple=True,
        help='Add or update a resource to a Windows executable. The RESOURCE is one to four items, '
        'FILE[,TYPE[,NAME[,LANGUAGE]]]. FILE can be a data file or an exe/dll. For data files, '
        'at least TYPE and NAME must be specified. LANGUAGE defaults to 0 or may be specified '
        'as wildcard * to update all resources of the given TYPE and NAME. For exe/dll files, '
        'all resources from FILE will be added/updated to the final executable if TYPE, NAME '
        'and LANGUAGE are omitted or specified as wildcard *. This option can be used multiple '
        'times.'
    )(cmd)
    cmd = optgroup.option(
        '--uac-admin',
        'uac_admin',
        is_flag=True,
        default=False,
        help='Request elevation to administrator permissions upon launch of the executable.'
    )(cmd)
    cmd = optgroup.option(
        '--uac-uiaccess',
        'uac_uiaccess',
        is_flag=True,
        default=False,
        help='Using this option allows an elevated application to work with Remote Desktop.'
    )(cmd)
    cmd = optgroup('Windows specific options')(cmd)

    # Group: Windows and macOS specific options

    cmd = optgroup.option(
        '-c/-w',
        '--console/--noconsole',
        '--nowindowed/--windowed',
        'console',
        default=True,
        help='Windows and macOS X: set whether or not to provide a console window for standard IO. '
        'On macOS X this will trigger building a `.app` bundle if there is no console window. '
        'This option is automatically set to true on Windows if the first script is a `.pyw` file. '
        'This option is ignored on *NIX systems.'
    )(cmd)
    cmd = optgroup.option(
        '-i',
        '--icon',
        'icon_file',
        metavar='<FILE.ico or FILE.exe,ID or FILE.icns or NONE>',
        help='FILE.ico: apply the icon to the built executable if running on Windows. FILE.exe,ID: extract the '
        'icon with the identifier ID from the specified executable and apply it to the built executable '
        'if running on Windows. FILE.icns: apply the icon to the .app bundle on macOS. NONE: don\'t apply '
        'any icon, thereby making the OS show a default icon. (default: apply PyInstaller\'s icon)'
    )(cmd)
    cmd = optgroup.option(
        '--disable-windowed-traceback',
        'disable_windowed_traceback',
        default=False,
        is_flag=True,
        help='Disable traceback dump of unhandled exception in windowed (noconsole) mode '
        '(Windows and macOS only), and instead display a message that this feature is disabled.'
    )(cmd)
    cmd = optgroup('Windows and macOS specific options')(cmd)

    # Group: Where to search

    cmd = optgroup.option(
        '--additional-hooks-dir',
        'hookspath',
        multiple=True,
        type=click.Path(),
        help='Additional path to search for hooks. This option can be used multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '-p',
        '--paths',
        multiple=True,
        type=click.Path(),
        help='A path to search for imports (like using PYTHONPATH). '
        f'Multiple paths are allowed, separated by ``{os.pathsep}``, or '
        'use this option multiple times. Equivalent to '
        'supplying the ``pathex`` argument in the spec file.'
    )(cmd)
    cmd = optgroup('Where to search')(cmd)

    # Group: What to bundle

    cmd = optgroup.option(
        '--runtime-hook',
        'runtime_hooks',
        multiple=True,
        type=click.File(),
        help='Path to a custom runtime hook file. A runtime hook is code that '
        'is bundled with the executable and is executed before any '
        'other code or module to set up special features of the runtime '
        'environment. This option can be used multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--collect-metadata-recursive',
        multiple=True,
        metavar='PACKAGENAME',
        help='Recursively collect all metadata from the specified package and it\'s dependencies. '
        'This option can be use multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--collect-metadata',
        multiple=True,
        metavar='PACKAGENAME',
        type=str,
        help='Collect all metadata from the specified package. '
        'This option can be use multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--collect-all',
        multiple=True,
        metavar='MODULENAME',
        type=click.UNPROCESSED,
        callback=lambda _, _p, value: [x for x in value if is_ident(x)],
        help='Collect all submodules, data files, metadata, and binaries from the specified package or module. '
        'This option can be use multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--collect-binaries',
        multiple=True,
        metavar='MODULENAME',
        type=click.UNPROCESSED,
        callback=lambda _, _p, value: [x for x in value if is_ident(x)],
        help='Collect all binaries from the specified package or module. '
        'This option can be use multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--collect-datas',
        multiple=True,
        metavar='MODULENAME',
        type=click.UNPROCESSED,
        callback=lambda _, _p, value: [x for x in value if is_ident(x)],
        help='Collect all data files from the specified package or module. '
        'This option can be use multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--collect-submodules',
        multiple=True,
        metavar='MODULENAME',
        type=click.UNPROCESSED,
        callback=lambda _, _p, value: [x for x in value if is_ident(x)],
        help='Collect all submodules from the specified package or module. '
        'This option can be used multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--excluded-import',
        'excludes',
        multiple=True,
        metavar='MODULENAME',
        type=click.UNPROCESSED,
        callback=lambda _, _p, value: [x for x in value if is_ident(x)],
        help='Optional module (Python name) that will be ignored and not included, '
        'as if it was not found. This option can be used multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '-H',
        '--hidden-import',
        '--hiddenimport',
        'hiddenimports',
        multiple=True,
        metavar='MODULENAME',
        type=click.UNPROCESSED,
        callback=lambda _, _p, value: [x for x in value if is_ident(x)],
        help='An import not visible in the code of the script(s) or it\'s dependencies. '
        'This option can be used multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--add-binary',
        'binaries',
        nargs=2,
        multiple=True,
        metavar=f'SRC DEST',
        help='Additional binary files to be added to the executable. '
        'This option can be used multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--add-data',
        'datas',
        nargs=2,
        multiple=True,
        metavar=f'SRC DEST',
        help='Additional non-binary files or folders to be added to the executable. '
        'This option can be used multiple times.'
    )(cmd)
    cmd = optgroup.option(
        '--upx-exclude',
        'upx_exclude',
        multiple=True,
        metavar='FILE',
        help='Prevent a binary from being compressed when using upx. This is typically'
        ' used if upx corrupts certain binaries during compression. FILE is the '
        'filename of the binary without path. This option can be used multiple times.'
    )(cmd)
    cmd = optgroup('What to bundle')(cmd)

    # Group: What to generate
    cmd = optgroup.option('--noupx', is_flag=True, default=False,
                          help='Don\'t apply UPX, regardless of availability')(cmd)
    cmd = optgroup.option(
        '-s',
        '--strip',
        is_flag=True,
        default=False,
        help='Apply a symbol-table strip to the executable and shared libraries. '
        '(not recommended on Windows)'
    )(cmd)
    cmd = optgroup.option(
        '-d',
        '--debug',
        multiple=True,
        type=click.Choice(['all', 'imports', 'bootloader', 'noarchive']),
        help=(
            'Whether or not to build a debug version of your code. '
            'This option can be used multiple times to select '
            'several of the following items.\n\n'
            '- bootloader: enable the bootloader\'s logging feature, '
            '              which prints launch progress messages.\n\n'
            '- imports: specify the -v option to the bundled Python '
            'interpreter. See ``python --help -v`` for more information '
            'on the effects of this option.\n\n'
            '- noarchive: instead of storing all frozen Python source '
            'files inside the executable file, store them as files '
            'alongside it.'
        )
    )(cmd)
    cmd = optgroup.option(
        '--splash',
        type=click.File(),
        help='(UNSTABLE) Add an splash screen with the image IMAGE_FILE to the application. '
        'The splash screen can display progress updates while unpacking.'
    )(cmd)
    cmd = optgroup.option('--key', metavar='KEY', help='The key used to encrypt python bytecode')(cmd)
    cmd = optgroup.option(
        '-F/-D',
        '--onefile/--onedir',
        'onefile',
        default=False,
        help='Single file or single directory bundle (default: onedir)'
    )(cmd)
    cmd = optgroup.option(
        '--specpath',
        type=click.Path(),
        default='.',
        help='Folder to store the generated spec file in (default : current directory)'
    )(cmd)
    cmd = optgroup.option(
        '-n',
        '--name',
        type=click.STRING,
        required=False,
        metavar='NAME',
        help='Name to assign to the bundled app and spec file (default: first script\'s basename)'
    )(cmd)
    cmd = optgroup('What to generate')(cmd)

    return cmd
