## Hook for PyOpenGL 3.x versions from 3.0.0b6 up. Previous versions have a
## plugin system based on pkg_resources which is problematic to handle correctly
## under pyinstaller; 2.x versions used to run fine without hooks, so this one
## shouldn't hurt.

import os
import sys

## PlatformPlugin performs a conditional import based on os.name and
## sys.platform. pyinstaller misses this so let's add it ourselves...

if os.name == 'nt':
    hiddenimports = ['OpenGL.platform.win32']
else:
    if sys.platform == 'linux2':
        hiddenimports = ['OpenGL.platform.glx']
    elif sys.platform[:6] == 'darwin':
        hiddenimports = ['OpenGL.platform.darwin']
    else:
        print 'ERROR: hook-OpenGL: Unrecognised combo (os.name: %s, sys.platform: %s)' % (os.name, sys.platform)


## arrays modules are needed too

hiddenimports += ['OpenGL.arrays.ctypesparameters',
                  'OpenGL.arrays.numarrays',
                  'OpenGL.arrays._numeric',
                  'OpenGL.arrays._strings',
                  'OpenGL.arrays.ctypespointers',
                  'OpenGL.arrays.lists',
                  'OpenGL.arrays.numbers',
                  'OpenGL.arrays.numeric',
                  'OpenGL.arrays.strings',
                  'OpenGL.arrays.ctypesarrays',
                  'OpenGL.arrays.nones',
                  'OpenGL.arrays.numericnames',
                  'OpenGL.arrays.numpymodule',
                  'OpenGL.arrays.vbo',
                  ]
