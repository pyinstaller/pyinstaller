import os
import sys

if __name__ == "__main__":
    fn =  os.path.join(os.path.dirname(sys.executable),
                       "..", "test_nestedlaunch0", "test_nestedlaunch0.exe")
    try:
        import subprocess
    except ImportError:
        if os.system(fn) != 0:
            raise RuntimeError("os.system failed: %s" % fn)
    else:
        subprocess.check_call([fn])
