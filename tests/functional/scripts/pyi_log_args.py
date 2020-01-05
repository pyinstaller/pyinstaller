import os
import sys

if len(sys.argv) > 1:
    basedir = os.path.dirname(sys.executable)
    # if script is inside .app package
    if os.path.basename(basedir) == 'MacOS':
        basedir = os.path.abspath(
            os.path.join(basedir, os.pardir, os.pardir, os.pardir))

    logfile = os.path.join(basedir, 'args.log')
    with open(logfile, 'w') as file:
        for arg in sys.argv[1:]:
            file.write(arg)
