# -*- mode: python -*-

import sys
if not sys.platform.startswith("darwin"):
    raise RuntimeError("please port test15 under linux2 and win32")

import os

# If the required dylib does not reside in the current directory, the Analysis
# class machinery, based on ctypes.util.find_library, will not find it. This was
# done on purpose for this test, to show how to give Analysis class a clue.
os.environ["DYLD_LIBRARY_PATH"] = "ctypes/"

# Check for presence of testctypes shared library, build it if not present
if not os.path.exists("ctypes/testctypes.dylib"):
    os.chdir("ctypes")
    os.system("gcc -Wall -dynamiclib testctypes.c -o testctypes.dylib -headerpad_max_install_names")
    id_dylib = os.path.abspath("testctypes.dylib")
    os.system("install_name_tool -id %s testctypes.dylib" % (id_dylib,))
    os.chdir("..")

__testname__ = 'test15'

a = Analysis(['../support/_mountzlib.py',
              '../support/useUnicode.py',
              'test15.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          name=os.path.join('dist', __testname__),
          debug=False,
          strip=False,
          upx=False,
          console=1 )
