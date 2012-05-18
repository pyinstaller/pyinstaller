#
# Copyright (C) 2012, Martin Zibricky
# Copyright (C) 2011, Hartmut Goebel
# Copyright (C) 2005, Giovanni Bajo
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


import os
import re
import sys

import PyInstaller.bindepend

from PyInstaller.compat import is_win, is_darwin, is_unix
from PyInstaller.build import Tree
from PyInstaller.hooks.hookutils import exec_statement, logger


def _find_tk_win(binaries):
    tcl_root = tk_root = None
    pattern = re.compile(r'(?i)tcl(\d)(\d)\.dll')

    for nm, fnm in binaries:
        mo = pattern.match(nm)
        if not mo:
            continue
        tclbindir = os.path.dirname(fnm)
        # Either Python21/DLLs with the .tcl files in
        #        Python21/tcl/tcl8.3 and Python21/tcl/tk8.3
        # or D:/Programs/Tcl/bin with the .tcl files in
        #    D:/Programs/Tcl/lib/tcl8.0 and D:/Programs/Tcl/lib/tk8.0
        ver = '.'.join(mo.groups())
        tclnm = 'tcl%s' % ver
        tknm = 'tk%s' % ver
        for attempt in ['../tcl', '../lib']:
            if os.path.exists(os.path.join(tclbindir, attempt, tclnm)):
                tcl_root = os.path.join(tclbindir, attempt, tclnm)
                tk_root = os.path.join(tclbindir, attempt, tknm)

    return tcl_root, tk_root


def _find_tk_darwin_frameworks(binaries):
    """
    Tcl and Tk are installed as Mac OS X Frameworks.
    """
    tcl_root = tk_root = None
    for nm, fnm in binaries:
        if nm == 'Tcl':
            tcl_root = os.path.join(os.path.dirname(fnm), 'Resources/Scripts')
        if nm == 'Tk':
            tk_root = os.path.join(os.path.dirname(fnm), 'Resources/Scripts')
    return tcl_root, tk_root


def _find_tk_tclshell():
    """
    Get paths to Tcl/Tk from the Tcl shell command 'info library'.

    This command will return path to TCL_LIBRARY.
    On most systems are Tcl and Tk libraries installed
    in the same prefix.
    """
    tcl_root = tk_root = None

    # Python code to get path to TCL_LIBRARY.
    code = 'from Tkinter import Tcl; t = Tcl(); print t.eval("info library")'

    tcl_root = exec_statement(code)
    tk_version = exec_statement('from _tkinter import TK_VERSION as v; print v')
    # TK_LIBRARY is in the same prefix as Tcl.
    tk_root = os.path.join(os.path.dirname(tcl_root), 'tk%s' % tk_version)
    return tcl_root, tk_root


def _find_tk_unix(binaries):
    """
    Tcl and Tk are installed to a specific prefix e.g. '/usr' on Linux or
    as not Frameworks on Mac OS X.
    """
    tcl_root = tk_root = None
    # Match .so and .dylib files.
    pattern = re.compile(r'libtcl(\d\.\d)?\.(so|dylib)')
    for nm, fnm in binaries:
        mo = pattern.match(nm)
        if not mo:
            continue
        tclbindir = os.path.dirname(fnm)
        ver = mo.group(1)
        if ver is None:
            # We found "libtcl.so.0" so we need to get the version
            # from the lib directory.
            for name in os.listdir(tclbindir):
                mo = re.match(r'tcl(\d.\d)', name)
                if mo:
                    ver = mo.group(1)
                    break
        # Linux: /usr/lib with the .tcl files in /usr/lib/tcl8.3
        #        and /usr/lib/tk8.3
        tcl_root = os.path.join(tclbindir, 'tcl%s' % ver)
        tk_root = os.path.join(tclbindir, 'tk%s' % ver)
        print tcl_root
        print tk_root
    return tcl_root, tk_root


def _find_tk(mod):
    """
    Find paths with Tcl and Tk data files to be bundled by PyInstaller.

    Return:
        tcl_root  path to Tcl data files.
        tk_root   path to Tk data files.
    """
    bins = PyInstaller.bindepend.selectImports(mod.__file__)

    if is_darwin:
        # _tkinter depends on system Tcl/Tk frameworks.
        if not bins:
            # 'mod.binaries' can't be used because on Mac OS X _tkinter.so
            # might depend on system Tcl/Tk frameworks and these are not
            # included in 'mod.binaries'.
            bins = PyInstaller.bindepend.getImports(mod.__file__)
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
            tcl_tk = _find_tk_darwin_frameworks(bins)
        # Tcl/Tk compiled as on Linux other Unices.
        # For example this is the case of Tcl/Tk from macports.
        else:
            tcl_tk = _find_tk_tclshell()

    else:
        tcl_tk = _find_tk_tclshell()

    return tcl_tk


def _collect_tkfiles(mod):
    tcl_root, tk_root = _find_tk(mod)

    tcldir = "tcl"
    tkdir = "tk"

    tcltree = Tree(tcl_root, os.path.join('_MEI', tcldir),
                   excludes=['demos', 'encoding', '*.lib', 'tclConfig.sh'])
    tktree = Tree(tk_root, os.path.join('_MEI', tkdir),
                  excludes=['demos', 'encoding', '*.lib', 'tkConfig.sh'])
    return (tcltree + tktree)


def hook(mod):
    # If not supported platform, skip TCL/TK detection.
    if not (is_win or is_darwin or is_unix):
        logger.info("... skipping TCL/TK detection on this platform (%s)",
                sys.platform)
        return mod

    # Get the Tcl/Tk data files for bundling with executable.
    try:
        tk_files = _collect_tkfiles(mod)
        mod.datas.extend(tk_files)
    except:
        logger.error("could not find TCL/TK")

    return mod
