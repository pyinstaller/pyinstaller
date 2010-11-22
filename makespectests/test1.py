import os
import sys
MST_DIR = os.path.abspath(os.path.split(sys.argv[0])[0])
HOME = os.path.normpath(os.path.join(MST_DIR, ".."))
TEST_FILE = os.path.join(MST_DIR, "script_for_tests.py")

if __name__ == "__main__":
    print "######## Checking the result of --onedir Makespec option"

    if not os.path.isfile(TEST_FILE):
        raise SystemExit("Test file %s missing" % TEST_FILE)
    res = os.system("%s %s" % (os.path.join(HOME, "Makespec.py --onedir"), TEST_FILE))

    if res == 0:
        res = os.system("%s %s.spec" % (os.path.join(HOME, "Build.py -y"), os.path.splitext(TEST_FILE)[0]))
    else:
        raise SystemExit("No spec file generated.")

    print "######## --onedir option test ends with success"