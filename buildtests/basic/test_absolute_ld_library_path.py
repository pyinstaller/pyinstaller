# LD_LIBRARY_PATH set by bootloader should not contain ./

import os
import sys

libpath = os.path.normpath(os.path.abspath(os.path.dirname(sys.executable)))
libpath += '/'
print('LD_LIBRARY_PATH: ' + libpath)
assert libpath == os.environ.get('LD_LIBRARY_PATH')


# for Mac OS X DYLD_LIBRARY_PATH is also set
if sys.platform == 'darwin':
    print('DYLD_LIBRARY_PATH: ' + libpath)
    assert libpath == os.environ.get('DYLD_LIBRARY_PATH')
