# distutils module requires Makefile and pyconfig.h files from Python
# installation.

import os
from distutils import sysconfig

makefile = sysconfig.get_config_h_filename()
config_h = sysconfig.get_makefile_filename()

print('pyconfig.h: ' + makefile)
print('Makefile: ' + config_h)


for f in (makefile, config_h):
    if not os.path.exists(f):
        raise SystemExit('File does not exist: %s' % f)
