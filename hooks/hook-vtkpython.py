# courtesy of David C. Morrill (4/2/2002)
import os
if os.name == 'posix':
   hiddenimports = ['libvtkCommonPython','libvtkFilteringPython','libvtkIOPython','libvtkImagingPython','libvtkGraphicsPython','libvtkRenderingPython','libvtkHybridPython','libvtkParallelPython','libvtkPatentedPython']
else:
   hiddenimports = ['vtkCommonPython','vtkFilteringPython','vtkIOPython','vtkImagingPython','vtkGraphicsPython','vtkRenderingPython','vtkHybridPython','vtkParallelPython','vtkPatentedPython']

