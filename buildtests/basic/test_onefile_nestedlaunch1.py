import os
import sys


if __name__ == '__main__':

    filename =  os.path.join(os.path.dirname(sys.executable),
            'test_onefile_nestedlaunch0')

    # On Windows append .exe suffix.
    if sys.platform.startswith('win'):
        filename += '.exe'

    try:
        import subprocess
    except ImportError:
        if os.system(filename) != 0:
            raise RuntimeError("os.system failed: %s" % filename)
    else:
        subprocess.check_call([filename])
