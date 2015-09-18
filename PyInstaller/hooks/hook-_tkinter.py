#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys

from PyInstaller.compat import is_win, is_darwin, is_unix, is_venv, base_prefix
from PyInstaller.compat import modname_tkinter
from PyInstaller.depend.bindepend import selectImports, getImports
from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import exec_statement, logger


def _handle_broken_tcl_tk():
    """
    When freezing from a Windows venv, overwrite the values of the standard
    `${TCL_LIBRARY}`, `${TK_LIBRARY}`, and `${TIX_LIBRARY}` environment
    variables.

    This is a workaround for broken Tcl/Tk detection in Windows virtual
    environments. Older versions of `virtualenv` set such variables erroneously,
    preventing PyInstaller from properly detecting Tcl/Tk. This issue has been
    noted for `virtualenv` under Python 2.4 and Windows 7.

    See Also
    -------
    https://github.com/pypa/virtualenv/issues/93
    """
    if is_win and is_venv:
        basedir = os.path.join(base_prefix, 'tcl')
        files = os.listdir(basedir)

        # Detect Tcl/Tk paths.
        for f in files:
            abs_path = os.path.join(basedir, f)
            if f.startswith('tcl') and os.path.isdir(abs_path):
                os.environ['TCL_LIBRARY'] = abs_path
            elif f.startswith('tk') and os.path.isdir(abs_path):
                os.environ['TK_LIBRARY'] = abs_path
            elif f.startswith('tix') and os.path.isdir(abs_path):
                os.environ['TIX_LIBRARY'] = abs_path


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
    from PyInstaller.lib.macholib import util

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
    with open(init_resource, 'r') as init_file:
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


def _find_tcl_tk_darwin_frameworks(binaries):
    """
    Get an OS X-specific 2-tuple of the absolute paths of the top-level
    external data directories for both Tcl and Tk, respectively.

    Under OS X, Tcl and Tk are installed as Frameworks requiring special care.

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
        'from %s import Tcl; print(Tcl().eval("info library"))' % modname_tkinter)
    tk_version = exec_statement(
        'from _tkinter import TK_VERSION; print(TK_VERSION)')

    # TK_LIBRARY is in the same prefix as Tcl.
    tk_root = os.path.join(os.path.dirname(tcl_root), 'tk%s' % tk_version)
    return tcl_root, tk_root


def _find_tcl_tk(mod):
    """
    Get a platform-specific 2-tuple of the absolute paths of the top-level
    external data directories for both Tcl and Tk, respectively.

    Returns
    -------
    list
        2-tuple whose first element is the value of `${TCL_LIBRARY}` and whose
        second element is the value of `${TK_LIBRARY}`.
    """
    bins = selectImports(mod.__file__)

    if is_darwin:
        # _tkinter depends on system Tcl/Tk frameworks.
        # For example this is the case of Python from homebrew.
        if not bins:
            # 'mod.binaries' can't be used because on Mac OS X _tkinter.so
            # might depend on system Tcl/Tk frameworks and these are not
            # included in 'mod.binaries'.
            bins = getImports(mod.__file__)
            # Reformat data structure from
            #     set(['lib1', 'lib2', 'lib3'])
            # to
            #     [('Tcl', '/path/to/Tcl'), ('Tk', '/path/to/Tk')]
            mapping = {}
            for l in bins:
                mapping[os.path.basename(l)] = l
            bins = [
                ('Tcl', mapping['Tcl']),
                ('Tk', mapping['Tk']),
            ]

        # _tkinter depends on Tcl/Tk compiled as frameworks.
        path_to_tcl = bins[0][1]
        if 'Library/Frameworks' in path_to_tcl:
            tcl_tk = _find_tcl_tk_darwin_frameworks(bins)
        # Tcl/Tk compiled as on Linux other Unixes.
        # For example this is the case of Tcl/Tk from macports.
        else:
            tcl_tk = _find_tcl_tk_dir()

    else:
        tcl_tk = _find_tcl_tk_dir()

    return tcl_tk


def _collect_tcl_tk_files(mod):
    """
    Get a list of TOC-style 3-tuples describing all external Tcl/Tk data files.

    Returns
    -------
    Tree
        Such list.
    """
    # Workaround for broken Tcl/Tk detection in virtualenv on Windows.
    _handle_broken_tcl_tk()

    tcl_root, tk_root = _find_tcl_tk(mod)

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

    return (tcltree + tktree)


def hook(mod):
    # Use a hook-function to get the module's attr:`__file__` easily.
    """
    Freeze all external Tcl/Tk data files if this is a supported platform *or*
    log a non-fatal error otherwise.
    """
    if is_win or is_darwin or is_unix:
        # _collect_tcl_tk_files(mod) returns a Tree (which is okay),
        # so we need to store it into `mod.datas` to prevent
        # `building.imphook.format_binaries_and_datas` from crashing
        # with "too many values to unpack".
        mod.datas = _collect_tcl_tk_files(mod)
    else:
        logger.error("... skipping Tcl/Tk handling on unsupported platform %s", sys.platform)

    return mod
