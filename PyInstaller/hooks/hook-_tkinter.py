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
    # Add all Tcl/Tk data files, based on the `TclTkInfo.data_files`. If Tcl/Tk is unavailable, the list is empty.
    #
    # NOTE: the list contains 3-element TOC tuples with full destination filenames (because other parts of code,
    # specifically splash-screen writer, currently require this format). Therefore, we need to use
    # `PostGraphAPI.add_datas` (which supports 3-element TOC tuples); if this was 2-element "hook-style" TOC list,
    #  we could just assign `datas` global hook variable, without implementing the post-graph `hook()` function.
    hook_api.add_datas(tcltk_info.data_files)
