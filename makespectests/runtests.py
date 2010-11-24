#!/usr/bin/env python
import glob
import os, sys
import shutil
import unittest

MST_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
HOME = os.path.normpath(os.path.join(MST_DIR, ".."))
MAKESPEC_EXE = os.path.join(HOME, "Makespec.py")
BUILD_EXE = os.path.join(HOME, "Build.py")
SCRIPT_FOR_TESTS = os.path.join(MST_DIR, "script_for_tests.py")
LOG_FILE = os.path.join(MST_DIR, "run.log")
CLEANUP = ["logdict*", "warn*.txt", "*.py[co]", "*/*.py[co]",
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

def build(specfile):
    global lastEdited
    lastEdited = specfile
    return os.system("%s -y %s >> %s" % (BUILD_EXE, specfile, LOG_FILE))

def makespec(scriptfile, newscriptname = None, dep_mode = "--onedir"):
    global lastEdited
    lastEdited = scriptfile
    name = os.path.splitext(scriptfile)[0]
    if newscriptname == None:
        newscriptname = name
    return os.system("%s -n %s %s %s >> %s" % (MAKESPEC_EXE, newscriptname,
        dep_mode, scriptfile, LOG_FILE))


class MakespecTest(unittest.TestCase):
    def tearDown(self):
        clean(["dist/", "build/"])

    def test_build_onedir(self):
        """BUILDING ONEDIR SPEC DEPLOYMENT"""
        res = makespec(SCRIPT_FOR_TESTS, "spec_od")
        self.assertEqual(res, 0, newSpecFail())
        res = build("spec_od.spec")
        self.assertEqual(res, 0, buildFail())

    def test_build_onefile(self):
        """BUILDING ONEFILE SPEC DEPLOYMENT"""
        res = makespec(SCRIPT_FOR_TESTS, "spec_of", "--onefile")
        self.assertEqual(res, 0, newSpecFail())
        res = build("spec_of.spec")
        self.assertEqual(res, 0, buildFail())

    def test_edited_file(self):
        """BUILDING AN EDITED SPEC"""
        # edit the to_edit.spec file before running this test
        res = makespec(SCRIPT_FOR_TESTS, "to_edit")
        self.assertEqual(res, 0, newSpecFail())
        res = build("to_edit.spec")
        self.assertEqual(res, 0, buildFail())

    def test_switch_to_onedir(self):
        """ONEFILE TO ONEDIR DEPLOYMENT"""
        res = makespec(SCRIPT_FOR_TESTS, "spec_of", "--onefile")
        self.assertEqual(res, 0, newSpecFail())
        res = makespec("spec_of.spec", "_spec_od")
        self.assertEqual(res, 0, switchSpecFail())
        res = build("_spec_od.spec")
        self.assertEqual(res, 0, buildFail())

    def test_switch_to_onefile(self):
        """ONEDIR TO ONEFILE DEPLOYMENT"""
        res = makespec(SCRIPT_FOR_TESTS, "spec_od")
        self.assertEqual(res, 0, newSpecFail())
        res = makespec("spec_od.spec", "_spec_of", "--onefile")
        self.assertEqual(res, 0, switchSpecFail())
        res = build("_spec_of.spec")
        self.assertEqual(res, 0, buildFail())

    def test_switch_to_onefile_edited_file(self):
        """SWITCHING AN EDITED SPEC FILE"""
        res = makespec(SCRIPT_FOR_TESTS, "to_edit")
        self.assertEqual(res, 0, newSpecFail())
        res = makespec("to_edit.spec", "_to_edit", "--onefile")
        self.assertEqual(res, 0, switchSpecFail())
        res = build("_to_edit.spec")
        self.assertEqual(res, 0, buildFail())

if __name__ == "__main__":
    os.chdir(MST_DIR)
    open(LOG_FILE, 'w').write('')
    suite = unittest.TestLoader().loadTestsFromTestCase(MakespecTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
    clean()
