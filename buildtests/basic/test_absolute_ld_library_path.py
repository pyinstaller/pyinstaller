# LD_LIBRARY_PATH set by bootloader should not contain ./
# 
# This test assumes the LD_LIBRARY_PATH is not set before running the test. 
# If you experience that this test fails, try to unset the variable and rerun the test. 
# This is how it is done in bash: 
# 
#  $ cd buildtests 
#  $ unset LD_LIBRARY_PATH 
#  $ ./runtests.py basic/test_absolute_ld_library_path.py 

import os
import sys

# For Linux/Solaris only
libpath = os.path.normpath(os.path.abspath(os.path.dirname(sys.executable)))
libpath += '/'

print('LD_LIBRARY_PATH expected: ' + libpath)
print('LD_LIBRARY_PATH  current: ' + os.environ.get('LD_LIBRARY_PATH'))
assert libpath == os.environ.get('LD_LIBRARY_PATH')
