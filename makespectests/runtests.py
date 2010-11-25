#!/usr/bin/env python
import glob
import os, sys
import shutil
import unittest
if sys.version_info < (2, 4):
    import commands
else:
    import subprocess

MST_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
HOME = os.path.normpath(os.path.join(MST_DIR, ".."))
MAKESPEC_EXE = os.path.join(HOME, "Makespec.py")
BUILD_EXE = os.path.join(HOME, "Build.py")
SCRIPT_FOR_TESTS = os.path.join(MST_DIR, "script_for_tests.py")
LOG_FILE = open(os.path.join(MST_DIR, "run.log"), 'w')
CLEANUP = ["logdict*", "warn*.txt", "*.py[co]", "*/*.py[co]", "build/", "dist/",
           "*/*/*.py[co]", "*_od.spec", "*_of.spec", "_*.spec"]
lastEdited = None
def newSpecFail(): return "Unable to makespec %s" % lastEdited
def switchSpecFail(): return "Unable to convert the %s" % lastEdited
def buildFail(): return "Unable to build the %s file" % lastEdited

def clean(to_clean=CLEANUP):
    """Cleaning tests resouces"""
    for clean in to_clean:
        clean = glob.glob(clean)
        for path in clean:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

def execute(cmdargs):
    if sys.version_info < (2, 4):
        cmd = " ".join(cmdargs)
        #TODO: how to redirect output?
        retcode, out = commands.getstatusoutput(cmd)
        #FIXME: commands is only for Unix!!!
    else:
        retcode = subprocess.Popen(cmdargs, stdout=open(os.devnull, 'w'), stderr=LOG_FILE).wait()
    return retcode

class MakespecTest(unittest.TestCase):
    def tearDown(self):
        clean()

    def build(self, specfile):
        global lastEdited
        lastEdited = specfile
        res = execute([BUILD_EXE, "-y", specfile])
        self.assertEqual(res, 0, buildFail())

    def makespec(self, scriptfile, newscriptname = None, dep_mode = "--onedir"):
        global lastEdited
        lastEdited = scriptfile
        name = os.path.splitext(scriptfile)[0]
        if newscriptname == None:
            newscriptname = name
        res = execute([MAKESPEC_EXE, "-n", newscriptname, dep_mode, scriptfile])
        if scriptfile.endswith(".spec"):
            self.assertEqual(res, 0, switchSpecFail())
        else:
            self.assertEqual(res, 0, newSpecFail())


    def test_build_onedir(self):
        """Building onedir spec deployment"""
        self.makespec(SCRIPT_FOR_TESTS, "spec_od")
        self.build("spec_od.spec")

    def test_build_onefile(self):
        """Building onefile spec deployment"""
        self.makespec(SCRIPT_FOR_TESTS, "spec_of", "--onefile")
        self.build("spec_of.spec")

    def test_edited_file(self):
        """Building an edited spec"""
        # edit the to_edit.spec file before running this test
        self.makespec(SCRIPT_FOR_TESTS, "to_edit")
        self.build("to_edit.spec")

    def test_switch_to_onedir(self):
        """Onefile to onedir deployment"""
        self.makespec(SCRIPT_FOR_TESTS, "spec_of", "--onefile")
        self.makespec("spec_of.spec", "_spec_od")
        self.build("_spec_od.spec")

    def test_switch_to_onefile(self):
        """Onedir to onefile deployment"""
        self.makespec(SCRIPT_FOR_TESTS, "spec_od")
        self.makespec("spec_od.spec", "_spec_of", "--onefile")
        self.build("_spec_of.spec")

    def test_switch_to_onefile_edited_file(self):
        """Switching an edited spec file"""
        self.makespec(SCRIPT_FOR_TESTS, "to_edit")
        self.makespec("to_edit.spec", "_to_edit", "--onefile")
        self.build("_to_edit.spec")

if __name__ == "__main__":
    os.chdir(MST_DIR)
    unittest.main()
