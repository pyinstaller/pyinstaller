#-----------------------------------------------------------------------------
# Copyright (c) 2013-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


import os
import sys
import locale

from PyInstaller.compat import is_win, is_darwin, is_unix, is_venv, \
    base_prefix, open_file, text_read_mode
from PyInstaller.depend.bindepend import selectImports, getImports
from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import exec_statement, logger


def _warn_if_activetcl_or_teapot_installed(tcl_root, tcltree):
    """
    If the current Tcl installation is a Teapot-distributed version of ActiveTcl
    *and* the current platform is OS X, log a non-fatal warning that the
    resulting executable will (probably) fail to run on non-host systems.

    PyInstaller does *not* freeze all ActiveTcl dependencies -- including
    Teapot, which is typically ignorable. Since Teapot is *not* ignorable in
    this case, this function warns of impending failure.

    See Also
    -------
    https://github.com/pyinstaller/pyinstaller/issues/621
    """
    from macholib import util

    # System libraries do not experience this problem.
    if util.in_system_path(tcl_root):
        return

    # Absolute path of the "init.tcl" script.
    try:
        init_resource = [r[1] for r in tcltree if r[1].endswith('init.tcl')][0]
    # If such script could not be found, silently return.
    except IndexError:
        return

    mentions_activetcl = False
    mentions_teapot = False
    # TCL/TK reads files using the `system encoding <https://www.tcl.tk/doc/howto/i18n.html#system_encoding>`_.
    with open_file(init_resource, text_read_mode,
                   encoding=locale.getpreferredencoding()) as init_file:
        for line in init_file.readlines():
            line = line.strip().lower()
            if line.startswith('#'):
                continue
            if 'activetcl' in line:
                mentions_activetcl = True
            if 'teapot' in line:
                mentions_teapot = True
            if mentions_activetcl and mentions_teapot:
                break

    if mentions_activetcl and mentions_teapot:
        logger.warning(
            """
You appear to be using an ActiveTcl build of Tcl/Tk, which PyInstaller has
difficulty freezing. To fix this, comment out all references to "teapot" in:

     %s

See https://github.com/pyinstaller/pyinstaller/issues/621 for more information.
            """ % init_resource)


def _find_tcl_tk_darwin_system_frameworks(binaries):
    """
    Get an OS X-specific 2-tuple of the absolute paths of the top-level
    external data directories for both Tcl and Tk, respectively.

    This function finds the OS X system installation of Tcl and Tk.
    System OS X Tcl and Tk are installed as Frameworks requiring special care.

    Returns
    -------
    list
        2-tuple whose first element is the value of `${TCL_LIBRARY}` and whose
        second element is the value of `${TK_LIBRARY}`.
    """
    tcl_root = tk_root = None
    for nm, fnm in binaries:
        if nm == 'Tcl':
            tcl_root = os.path.join(os.path.dirname(fnm), 'Resources/Scripts')
        elif nm == 'Tk':
            tk_root =  os.path.join(os.path.dirname(fnm), 'Resources/Scripts')
    return tcl_root, tk_root


def _find_tcl_tk_dir():
    """
    Get a platform-agnostic 2-tuple of the absolute paths of the top-level
    external data directories for both Tcl and Tk, respectively.

    Returns
    -------
    list
        2-tuple whose first element is the value of `${TCL_LIBRARY}` and whose
        second element is the value of `${TK_LIBRARY}`.
    """
    # Python code to get path to TCL_LIBRARY.
    tcl_root = exec_statement(
        'from tkinter import Tcl; print(Tcl().eval("info library"))')
    tk_version = exec_statement(
        'from _tkinter import TK_VERSION; print(TK_VERSION)')

    # TK_LIBRARY is in the same prefix as Tcl.
    tk_root = os.path.join(os.path.dirname(tcl_root), 'tk%s' % tk_version)
    return tcl_root, tk_root


def _find_tcl_tk(hook_api):
    """
    Get a platform-specific 2-tuple of the absolute paths of the top-level
    external data directories for both Tcl and Tk, respectively.

    Returns
    -------
    list
        2-tuple whose first element is the value of `${TCL_LIBRARY}` and whose
        second element is the value of `${TK_LIBRARY}`.
    """
    bins = selectImports(hook_api.__file__)

    if is_darwin:
        # _tkinter depends on system Tcl/Tk frameworks.
        # For example this is the case of Python from homebrew.
        if not bins:
            # 'hook_api.binaries' can't be used because on Mac OS X _tkinter.so
            # might depend on system Tcl/Tk frameworks and these are not
            # included in 'hook_api.binaries'.
            bins = getImports(hook_api.__file__)

            if bins:
                # Reformat data structure from
                #     set(['lib1', 'lib2', 'lib3'])
                # to
                #     [('Tcl', '/path/to/Tcl'), ('Tk', '/path/to/Tk')]
                mapping = {}
                for lib in bins:
                    mapping[os.path.basename(lib)] = lib
                bins = [
                    ('Tcl', mapping['Tcl']),
                    ('Tk', mapping['Tk']),
                ]
            else:
                # Starting with macOS 11, system libraries are hidden.
                # Until we adjust library discovery accordingly, bins
                # will end up empty. But this implicitly indicates that
                # the system framework is used, so return None, None
                # to inform the caller.
                return None, None

        # _tkinter depends on Tcl/Tk compiled as frameworks.
        path_to_tcl = bins[0][1]
        # OS X system installation of Tcl/Tk.
        # [/System]/Library/Frameworks/Tcl.framework/Resources/Scripts/Tcl
        if 'Library/Frameworks/Tcl.framework' in path_to_tcl:
            #tcl_tk = _find_tcl_tk_darwin_system_frameworks(bins)
            tcl_tk = None, None  # Do not gather system framework's data

        # Tcl/Tk compiled as on Linux other Unixes.
        # This is the case of Tcl/Tk from macports and Tck/Tk built into
        # python.org OS X python distributions.
        # python.org built-in tcl/tk is located at
        # /Library/Frameworks/Python.framework/Versions/3.x/lib/libtcl8.6.dylib
        else:
            tcl_tk = _find_tcl_tk_dir()

    else:
        tcl_tk = _find_tcl_tk_dir()

    return tcl_tk


def _collect_tcl_modules(tcl_root):
    """
    Get a list of TOC-style 3-tuples describing Tcl modules. The modules
    directory is separate from the library/data one, and is located
    at $tcl_root/../tclX, where X is the major Tcl version.

    Returns
    -------
    Tree
        Such list, if the modules directory exists.
    """

    # Obtain Tcl major version.
    tcl_version = exec_statement(
        'from tkinter import Tcl; print(Tcl().eval("info tclversion"))')
    tcl_version = tcl_version.split('.')[0]

    modules_dirname = 'tcl' + str(tcl_version)
    modules_path = os.path.join(tcl_root, '..', modules_dirname)

    if not os.path.isdir(modules_path):
        logger.warn('Tcl modules directory %s does not exist.', modules_path)
        return []

    return Tree(modules_path, prefix=modules_dirname)


def _collect_tcl_tk_files(hook_api):
    """
    Get a list of TOC-style 3-tuples describing all external Tcl/Tk data files.

    Returns
    -------
    Tree
        Such list.
    """
    tcl_root, tk_root = _find_tcl_tk(hook_api)

    # On macOS, we do not collect system libraries. Therefore, if system
    # Tcl/Tk framework is used, it makes no sense to collect its data,
    # either. In this case, _find_tcl_tk() will return None, None - either
    # deliberately (we found the data paths, but ignore them) or not
    # (starting with macOS 11, the data path cannot be found until shared
    # library discovery is fixed).
    if is_darwin and not tcl_root and not tk_root:
        logger.info('Not collecting Tcl/Tk data - either python is using '
                    'macOS\' system Tcl/Tk framework, or Tcl/Tk data '
                    'directories could not be found.')
        return []

    # TODO Shouldn't these be fatal exceptions?
    if not tcl_root:
        logger.error('Tcl/Tk improperly installed on this system.')
        return []
    if not os.path.isdir(tcl_root):
        logger.error('Tcl data directory "%s" not found.', tcl_root)
        return []
    if not os.path.isdir(tk_root):
        logger.error('Tk data directory "%s" not found.', tk_root)
        return []

    tcltree = Tree(
        tcl_root, prefix='tcl', excludes=['demos', '*.lib', 'tclConfig.sh'])
    tktree = Tree(
        tk_root, prefix='tk', excludes=['demos', '*.lib', 'tkConfig.sh'])

    # If the current Tcl installation is a Teapot-distributed version of
    # ActiveTcl and the current platform is OS X, warn that this is bad.
    if is_darwin:
        _warn_if_activetcl_or_teapot_installed(tcl_root, tcltree)

    # Collect Tcl modules
    tclmodulestree = _collect_tcl_modules(tcl_root)

    return (tcltree + tktree + tclmodulestree)


def hook(hook_api):
    # Use a hook-function to get the module's attr:`__file__` easily.
    """
    Freeze all external Tcl/Tk data files if this is a supported platform *or*
    log a non-fatal error otherwise.
    """
    if is_win or is_darwin or is_unix:
        # _collect_tcl_tk_files(hook_api) returns a Tree (which is okay),
        # so we need to store it into `hook_api.datas` to prevent
        # `building.imphook.format_binaries_and_datas` from crashing
        # with "too many values to unpack".
        hook_api.add_datas(_collect_tcl_tk_files(hook_api))
    else:
        logger.error("... skipping Tcl/Tk handling on unsupported platform %s", sys.platform)
