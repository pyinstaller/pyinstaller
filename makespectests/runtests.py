#!/usr/bin/env python
import glob
import os, sys
import shutil
import unittest

try:
    True, False
except:
    True = (1 == 1)
    False = not True

MST_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
HOME = os.path.normpath(os.path.join(MST_DIR, ".."))
MAKESPEC_EXE = os.path.join(HOME, "Makespec.py")
BUILD_EXE = os.path.join(HOME, "Build.py")
SCRIPT_FOR_TESTS = "test.py"
SCRIPT_FOR_TESTS_2 = "test2.py"
LOG_FILE = "err.log"
if os.name == "posix":
    NULL_DEV = "/dev/null"
else:
    NULL_DEV = "nul"
CLEANUP = ["build/", "dist/", "*.log", "warn*.txt", "*.py[co]", "*/*.py[co]",
           "*/*/*.py[co]", "*.spec", "*~"]
def clean(to_clean=CLEANUP):
    """Cleaning tests resouces"""
    for clean in to_clean:
        clean = glob.glob(clean)
        for path in clean:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

def execute(cmd):
    retcode = os.system('%s > %s 2> "%s"' % (cmd, NULL_DEV, LOG_FILE))
    errstring = "\nMore details:\n" + open(LOG_FILE, 'r').read()
    return retcode, errstring

class MakespecTest(unittest.TestCase):
    def tearDown(self):
        clean()

    def build(self, specfile="test.spec"):
        retcode, errstring = execute('"%s" -y %s' % (BUILD_EXE, specfile))
        self.assertEqual(retcode, 0, "Unable to build test.spec" + errstring)

    def makespec(self, scriptfile=SCRIPT_FOR_TESTS, scriptfile2=SCRIPT_FOR_TESTS_2,
                 dep_mode="--onedir", merge=False):
        if merge:
            retcode, errstring = execute('"%s" --merge %s %s %s' % (MAKESPEC_EXE, dep_mode, scriptfile, scriptfile2))
        else:
            retcode, errstring = execute('"%s" %s %s' % (MAKESPEC_EXE, dep_mode, scriptfile))

        if scriptfile.endswith(".spec"):
            self.assertEqual(retcode, 0, "Unable to convert test.spec" + errstring)
        else:
            self.assertEqual(retcode, 0, "Unable to makespec test.py" + errstring)

    def runExe(self, exename):
        retcode, errstring = execute("./%s" % exename)
        self.assertEqual(retcode, 0, ("Unable to run %s" % exename) + errstring)

    def editspec(self):
        specfile_content = open("test.spec", 'r').read()
        specfile_content = specfile_content.replace("name_of_exe = 'test'", "name_of_exe = 'edited'")
        specfile_content = specfile_content.replace("build_dir = 'build/pyi.linux2/test'", "build_dir = 'build/pyi.linux2/edited'")
        specfile_content = specfile_content.replace("useDebug = False", "useDebug = True")
        open("test.spec", 'w').write(specfile_content)

    # Tests are performed from here, in alphabetical order
    def test_build_onedir(self):
        """Building onedir spec deployment"""
        self.makespec()
        self.build()

    def test_build_onedir_merge(self):
        """Building merge onedir spec deployment"""
        self.makespec(merge=True)
        self.build()
        self.runExe("dist/test/test")
        self.runExe("dist/test/test2")

    def test_build_onefile(self):
        """Building onefile spec deployment"""
        self.makespec(dep_mode="--onefile")
        self.build()

    def test_build_onefile_merge(self):
        """Building merge onefile spec deployment"""
        self.makespec(dep_mode="--onefile", merge=True)
        self.build()
        self.runExe("dist/test/test")
        self.runExe("dist/test/test2")

    def test_edited_file(self):
        """Building an edited spec"""
        self.makespec()
        self.editspec()
        self.build()

    def test_switch_to_onedir(self):
        """Onefile to onedir deployment"""
        self.makespec(dep_mode="--onefile")
        self.makespec(scriptfile="test.spec")
        self.build()

    def test_switch_to_onefile(self):
        """Onedir to onefile deployment"""
        self.makespec()
        self.makespec(scriptfile="test.spec", dep_mode="--onefile")
        self.build()

    def test_switch_to_onefile_edited_file(self):
        """Switching an edited spec file"""
        self.makespec()
        self.editspec()
        self.makespec(scriptfile="test.spec", dep_mode="--onefile")
        self.build()

if __name__ == "__main__":
    os.chdir(MST_DIR)
    unittest.main()
