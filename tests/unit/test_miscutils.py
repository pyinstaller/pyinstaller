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

import os
import array
import shutil

import pytest

from PyInstaller import HOMEPATH, PLATFORM
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
            StringFileInfo([StringTable('040904b0', [StringStruct('FileDescription', 'versioninfo test')])]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])])
        ]
    )

    file = str(tmp_path / 'versioninfo')
    save_py_data_struct(file, vsinfo)

    assert vsinfo == load_py_data_struct(file)


@pytest.mark.win32
def test_versioninfo_str(tmp_path):
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
            StringFileInfo([StringTable('040904b0', [StringStruct('FileDescription', 'versioninfo test')])]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])])
        ]
    )

    # "Serialize" to string. This is what grab_version.py utility does to write VsVersionInfo to output text file.
    vs_info_str = str(vsinfo)

    # "Deserialize" via eval. This is what versioninfo.SetVersion() does to read VsVersionInfo from text file.
    vsinfo2 = eval(vs_info_str)

    assert vsinfo == vsinfo2


@pytest.mark.win32
def test_versioninfo_written_to_exe(tmp_path):
    from PyInstaller.utils.win32 import versioninfo
    from PyInstaller.utils.win32.versioninfo import VSVersionInfo, \
        FixedFileInfo, StringFileInfo, StringTable, StringStruct, \
        VarFileInfo, VarStruct

    # Test/expected values
    FILE_DESCRIPTION = 'versioninfo test'
    PRODUCT_NAME = 'Test Product'
    PRODUCT_VERSION = '2021.09.18.00'

    # Create a version info structure...
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
            StringFileInfo([
                StringTable(
                    '040904b0', [
                        StringStruct('FileDescription', FILE_DESCRIPTION),
                        StringStruct('ProductName', PRODUCT_NAME),
                        StringStruct('ProductVersion', PRODUCT_VERSION)
                    ]
                )
            ]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])])
        ]
    )

    # Locate bootloader executable
    bootloader_file = os.path.join(HOMEPATH, 'PyInstaller', 'bootloader', PLATFORM, 'run.exe')

    # Create a local copy
    test_file = str(tmp_path / 'test_file.exe')
    shutil.copyfile(bootloader_file, test_file)

    # Embed version info
    versioninfo.SetVersion(test_file, vsinfo)

    # Read back the values from the string table.
    def read_file_version_info(filename, *attributes):
        import ctypes
        winver = ctypes.WinDLL('version.dll')

        # Read the version information.
        info_len = winver.GetFileVersionInfoSizeW(filename, None)
        assert info_len, "No version information found!"
        info_buf = ctypes.create_string_buffer(info_len)
        rc = winver.GetFileVersionInfoW(filename, None, info_len, info_buf)
        assert rc, "Failed to read version information!"

        # Look for the codepages and take the first one.
        entry_ptr = ctypes.c_void_p()
        entry_len = ctypes.c_uint()
        winver.VerQueryValueW(info_buf, r'\VarFileInfo\Translation', ctypes.byref(entry_ptr), ctypes.byref(entry_len))
        assert entry_len.value, "No codepages found!"
        codepage = array.array('H', ctypes.string_at(entry_ptr.value, 4))
        codepage = "%04x%04x" % tuple(codepage)

        # Query attributes.
        attr_values = []
        for attr in attributes:
            entry_name = fr'\StringFileInfo\{codepage}\{attr}'
            rc = winver.VerQueryValueW(info_buf, entry_name, ctypes.byref(entry_ptr), ctypes.byref(entry_len))
            if not rc:
                entry_value = None
            else:
                entry_value = ctypes.wstring_at(entry_ptr.value, entry_len.value - 1)
            attr_values.append(entry_value)

        return attr_values

    values = read_file_version_info(test_file, 'FileDescription', 'ProductName', 'ProductVersion')
    assert values == [FILE_DESCRIPTION, PRODUCT_NAME, PRODUCT_VERSION]


CHINESE_LOREM_IPSUM = """
索感歴新策理通幻月続本初迷検価泉属速棄者。料流重者県作軽渡獲県行選見。意鑑民供変介画同表後院苦面例紙約度電心
時盤止野断希茶術同懲上権策全崎査応校匹国。真村辺名下周一場庭戸原図会正前対校米利。岩録開教純止表乗都偉別際政難然始京国京
校県水路中旅続球是校高約止性振下上派若福。案神整細番公流関閲元弊導説大実枝際確導
"""


def test_decode():
    """
    Test PyInstaller.utils.misc.decode().
    """
    import codecs
    from PyInstaller.utils.misc import decode

    # Test UTF8 with or without the BOM.
    assert decode(CHINESE_LOREM_IPSUM.encode()) == CHINESE_LOREM_IPSUM
    assert decode(codecs.BOM_UTF8 + CHINESE_LOREM_IPSUM.encode()) == CHINESE_LOREM_IPSUM

    # Test non-default UTF variants specified via a BOM.
    assert decode(codecs.BOM_UTF32_LE + codecs.utf_32_le_encode(CHINESE_LOREM_IPSUM)[0]) == CHINESE_LOREM_IPSUM
    assert decode(codecs.BOM_UTF16_BE + codecs.utf_16_be_encode(CHINESE_LOREM_IPSUM)[0]) == CHINESE_LOREM_IPSUM

    # Test using the encoding comment.
    with_cookie = "# encoding: gb18030\n" + CHINESE_LOREM_IPSUM
    assert decode(with_cookie.encode("GB18030")) == with_cookie
