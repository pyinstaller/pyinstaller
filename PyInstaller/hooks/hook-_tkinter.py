#-----------------------------------------------------------------------------
# Copyright (c) 2013-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks.tcl_tk import tcltk_info


def hook(hook_api):
    # Add all Tcl/Tk data files, based on the `TclTkInfo.data_files`.
    #
    # NOTE: the list contains 3-element TOC tuples with full destination filenames (because other parts of code,
    # specifically splash-screen writer, currently require this format). Therefore, we need to use
    # `PostGraphAPI.add_datas` (which supports 3-element TOC tuples); if this was 2-element "hook-style" TOC list,
    #  we could just assign `datas` global hook variable, without implementing the post-graph `hook()` function.

    # Check `TclTkInfo.tcl_data_missing` and `TclTkInfo.tk_data_missing` flags, which indicate that we expect
    # Tcl/Tk data directories to be collected AND they were not available; in this case, abort the build with
    # error. In earlier versions of PyInstaller, the corresponding error was raised at run time, by the
    # _tkinter run-time hook, but it is arguably better to catch these situations at build time. This also gives
    # us more flexibility in dealing with scenarios where we do not expect Tcl/Tk data directories to exist in
    # the first place.
    if tcltk_info.tcl_data_missing:
        raise SystemExit(f"ERROR: Tcl data/library directory ({tcltk_info.tcl_data_dir!r}) could not be collected!")

    if tcltk_info.tk_data_missing:
        raise SystemExit(f"ERROR: Tk data/library directory ({tcltk_info.tk_data_dir!r}) could not be collected!")

    hook_api.add_datas(tcltk_info.data_files)
