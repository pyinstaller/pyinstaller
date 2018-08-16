#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import glob
import os

from PyInstaller.utils.hooks import pyqt5_library_info, collect_system_data_files

hiddenimports = [
    # PyQt5.10 and earlier uses sip in an separate package;
    'sip',
    # PyQt5.11 and later provides SIP in a private package. Support both.
    'PyQt5.sip'
]

# Collect the ``qt.conf`` file.
datas = [x for x in
         collect_system_data_files(pyqt5_library_info.location['PrefixPath'],
                                   'PyQt5')
         if os.path.basename(x[0]) == 'qt.conf']


def find_all_or_none(globs_to_include, num_files):
    """
    globs_to_include is a list of file name globs
    If the number of found files does not match num_files
    then no files will be included.
    """
    # TODO: This function is required because CI is failing to include libEGL
    # The error in AppVeyor is:
    # [2312] LOADER: Running pyi_lib_PyQt5-uic.py
    # Failed to load libEGL (Access is denied.)
    # More info: https://github.com/pyinstaller/pyinstaller/pull/3568
    # Since the PyQt5 wheels do not include d3dcompiler_4?.dll, libEGL.dll and
    # libGLESv2.dll will not be included for PyQt5 builds during CI.
    to_include = []
    dst_dll_path = os.path.join('PyQt5', 'Qt', 'bin')
    for dll in globs_to_include:
        dll_path = os.path.join(pyqt5_library_info.location['BinariesPath'],
                                dll)
        dll_file_paths = glob.glob(dll_path)
        for dll_file_path in dll_file_paths:
            to_include.append((dll_file_path, dst_dll_path))
    if len(to_include) == num_files:
        return to_include
    return []


binaries = []
angle_files = ['libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_??.dll']
binaries += find_all_or_none(angle_files, 3)

opengl_software_renderer = ['opengl32sw.dll']
binaries += find_all_or_none(opengl_software_renderer, 1)

# Include ICU files, if they exist.
# See the "Deployment approach" section in ``PyInstaller/utils/hooks/qt.py``.
icu_files = ['icudt??.dll', 'icuin??.dll', 'icuuc??.dll']
binaries += find_all_or_none(icu_files, 3)
