# -*- mode: python -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import sys
import os


is_win = sys.platform.startswith('win')
is_darwin = sys.platform == 'darwin'  # Mac OS X


def mac_gcc_architecture():
    """
    Returns the -arch parameter for gcc on Mac OS X.
    """
    # Darwin's platform.architecture() is buggy and always
    # returns "64bit" event for the 32bit version of Python's
    # universal binary. So we roll out our own (that works
    # on Darwin).
    if sys.maxint > 2L ** 32:
        # 64bit
        return 'x86_64'
    else:
        # 32bit
        return 'i386'


CTYPES_DIR = 'ctypes'
TEST_LIB = os.path.join(CTYPES_DIR, 'testctypes')


if is_win:
    TEST_LIB += '.dll'
elif is_darwin:
    TEST_LIB += '.dylib'
else:
    TEST_LIB += '.so'


# If the required dylib does not reside in the current directory, the Analysis
# class machinery, based on ctypes.util.find_library, will not find it. This
# was done on purpose for this test, to show how to give Analysis class
# a clue.
if is_win:
    os.environ['PATH'] = os.path.abspath(CTYPES_DIR) + ';' + os.environ['PATH']
else:
    os.environ['LD_LIBRARY_PATH'] = CTYPES_DIR
    os.environ['DYLD_LIBRARY_PATH'] = CTYPES_DIR
    os.environ['LIBPATH'] = CTYPES_DIR


os.chdir(CTYPES_DIR)


if is_win:
    ret = os.system('cl /LD testctypes-win.c')
    if ret != 0:
        os.system('gcc -shared testctypes-win.c -o testctypes.dll')
elif is_darwin:
    # On Mac OS X we need to detect architecture - 32 bit or 64 bit.
    cmd = ('gcc -arch ' + mac_gcc_architecture() + ' -Wall -dynamiclib '
        'testctypes.c -o testctypes.dylib -headerpad_max_install_names')
    os.system(cmd)
    id_dylib = os.path.abspath('testctypes.dylib')
    os.system('install_name_tool -id %s testctypes.dylib' % (id_dylib,))
else:
    os.system('gcc -fPIC -shared testctypes.c -o testctypes.so')


os.chdir("..")


__testname__ = 'test_onefile_ctypes'

a = Analysis([__testname__ + '.py'],
             pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          name=__testname__ + '.exe',
          debug=False,
          strip=False,
          upx=False,
          console=False)
