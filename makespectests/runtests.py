#!/usr/bin/env python
import glob
import os, sys
import shutil

MST_DIR = os.path.abspath(os.path.split(sys.argv[0])[0])
HOME = os.path.normpath(os.path.join(MST_DIR, ".."))

TO_CLEAN = """python_exe.build
logdict*.log
warn*.txt
*.py[co]
*/*.py[co]
*/*/*.py[co]
build/
dist/
""".split()

def clean():
    for pattern in TO_CLEAN:
        clean_list = glob.glob(pattern)
        for path in clean_list:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except OSError, e:
                print e

if __name__ == "__main__":
    tests = glob.glob(os.path.join(MST_DIR, "test*.py"))
    for t in tests:
        testname = "%s" % os.path.basename(os.path.splitext(t)[0]).upper()
        print testname, ":"
        res = os.system("python %s" % t)
        if res != 0:
            raise SystemExit("%s failed." % t)

        clean()