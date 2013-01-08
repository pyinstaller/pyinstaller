# distutils module requires Makefile and pyconfig.h files from Python
# installation.

import os
import sys
import time
from distutils import sysconfig


config_h = sysconfig.get_config_h_filename()
print('pyconfig.h: ' + config_h)
files = [config_h]

# On Windows Makefile does not exist.
if not sys.platform.startswith('win'):
    makefile = sysconfig.get_makefile_filename()
    print('Makefile: ' + makefile)
    files.append(makefile)

time.sleep(30)

for f in files:
    if not os.path.exists(f):
        raise SystemExit('File does not exist: %s' % f)
