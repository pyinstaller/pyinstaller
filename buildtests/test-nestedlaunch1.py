import os
import sys

if __name__ == "__main__":
    if sys.version_info >= (2,5):
        import subprocess
        subprocess.check_call([os.path.dirname(sys.executable) + "/../test-nestedlaunch0/test-nestedlaunch0.exe"])
    else:
        fn = os.path.join(os.path.dirname(sys.executable), "..", "test-nestedlaunch0", "test-nestedlaunch0.exe")
        if os.system(fn) != 0:
            raise RuntimeError("os.system failed: %s" % fn)
