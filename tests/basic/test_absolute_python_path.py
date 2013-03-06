# sys.path  should contain absolute paths.
# With relative paths frozen application will
# fail to import modules when currect working
# directory is changed.

import os
import sys
import tempfile

print(sys.path)
print('CWD: ' + os.getcwdu())

# Change working directory.
os.chdir(tempfile.gettempdir())
print('Changing working directory...')
print('CWD: ' + os.getcwdu())

# Try import a module. It should fail
try:
    for pth in sys.path:
        if not os.path.isabs(pth):
            SystemExit('ERROR: sys.path not absolute')
    import datetime
except:
    SystemExit('ERROR: sys.path not absolute')
