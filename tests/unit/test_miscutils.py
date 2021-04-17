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


import pytest

from PyInstaller.utils.misc import load_py_data_struct, save_py_data_struct


@pytest.mark.win32
def test_versioninfo(tmp_path):
    from PyInstaller.utils.win32.versioninfo import VSVersionInfo, \
        FixedFileInfo, StringFileInfo, StringTable, StringStruct, \
        VarFileInfo, VarStruct

    vsinfo = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=(1, 2, 3, 4),
            prodvers=(5, 6, 7, 8),
            mask=0x3f,
            flags=0x1,
            OS=0x40004,
            fileType=0x42,
            subtype=0x42,
            date=(0, 0)
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        '040904b0',
                        [StringStruct('FileDescription',
                                      'versioninfo test')])
                ]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])])
        ]
    )

    file = str(tmp_path / 'versioninfo')
    save_py_data_struct(file, vsinfo)

    assert vsinfo == load_py_data_struct(file)
