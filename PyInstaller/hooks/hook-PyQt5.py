#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import os

from PyInstaller.utils.hooks import pyqt5_library_info, collect_system_data_files

hiddenimports = ['sip']

# Collect the ``qt.conf`` file.
datas = [x for x in
         collect_system_data_files(pyqt5_library_info.location['PrefixPath'],
                                   'PyQt5')
         if os.path.basename(x[0]) == 'qt.conf']

# Include ICU files, if they exist. See the "Deployment approach" section in
# ``PyInstaller/utils/hooks/qt.py``.
[(os.path.join(pyqt5_library_info.location['BinariesPath'], dll),
  os.path.join('PyQt5', 'Qt', 'bin', dll))
 for dll in ('icudt??.dll', 'icuin??.dll', 'icuuc??.dll')]

# TODO: Include software rendering for OpenGL. See the "Deployment approach". However, because the standard PyQt5 wheel `doesn't include <https://www.riverbankcomputing.com/pipermail/pyqt/2018-June/040387.html>`_ ``d3dcompiler_XX.dll``, this produces failures. When the wheel is updated, this code can be uncommented.
##binaries = []
##for dll in ('libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_??.dll', 'opengl32sw.dll'):
##    dll_path = os.path.join(pyqt5_library_info.location['BinariesPath'], dll)
##    # Only add files if they exist.
##    if glob(dll_path):
##        binaries += [(dll_path, os.path.join('PyQt5', 'Qt', 'bin', dll))]
