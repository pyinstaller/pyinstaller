#-----------------------------------------------------------------------------
# Copyright (c) 2013-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
if os.name == 'posix':
    hiddenimports = ['libvtkCommonPython','libvtkFilteringPython','libvtkIOPython','libvtkImagingPython','libvtkGraphicsPython','libvtkRenderingPython','libvtkHybridPython','libvtkParallelPython','libvtkPatentedPython']
else:
    hiddenimports = ['vtkCommonPython','vtkFilteringPython','vtkIOPython','vtkImagingPython','vtkGraphicsPython','vtkRenderingPython','vtkHybridPython','vtkParallelPython','vtkPatentedPython']
