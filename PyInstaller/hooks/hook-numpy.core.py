#-----------------------------------------------------------------------------
# Copyright (c) 2013-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
# On Windows, numpy depends on a set of dynamically-detemined DLLs, which means
# that PyInstaller's static analysis can't find them. See https://github.com/pyinstaller/pyinstaller/issues/1969
# for more information. The typical error message: ``Intel MKL FATAL ERROR:
# Cannot load mkl_intel_thread.dll.``
#
# So, include them manually.
import os
import os.path
from PyInstaller.utils.hooks import get_package_paths

pkg_base, pkg_dir = get_package_paths('numpy.core')
# Walk through all files in ``numpy.core``, looking for DLLs.
datas = []
for f in os.listdir(pkg_dir):
    extension = os.path.splitext(f)[1]
    if extension == '.dll':
        # Produce the tuple ('/abs/path/to/libs/numpy/core/file.dll', '')
        source = os.path.join(pkg_dir, f)
        datas.append((source, ''))
