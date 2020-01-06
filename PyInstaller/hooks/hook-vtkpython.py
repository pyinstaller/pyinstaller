#-----------------------------------------------------------------------------
# Copyright (c) 2013-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


import os
if os.name == 'posix':
    hiddenimports = ['libvtkCommonPython','libvtkFilteringPython','libvtkIOPython','libvtkImagingPython','libvtkGraphicsPython','libvtkRenderingPython','libvtkHybridPython','libvtkParallelPython','libvtkPatentedPython']
else:
    hiddenimports = ['vtkCommonPython','vtkFilteringPython','vtkIOPython','vtkImagingPython','vtkGraphicsPython','vtkRenderingPython','vtkHybridPython','vtkParallelPython','vtkPatentedPython']
