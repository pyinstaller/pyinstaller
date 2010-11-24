#!/usr/bin/env python
import glob
import os, sys
import shutil
import unittest

MST_DIR = os.path.abspath(os.path.split(sys.argv[0])[0])
HOME = os.path.normpath(os.path.join(MST_DIR, ".."))
MAKESPEC_EXE = os.path.join(HOME, "Makespec.py")
BUILD_EXE = os.path.join(HOME, "Build.py")
SCRIPT_FOR_TESTS = os.path.join(MST_DIR, "script_for_tests.py")
CLEANUP = """warn*.txt
*.py[co]
*/*.py[co]
*/*/*.py[co]
*_od.spec
*_of.spec
build/
dist/
""".split()
lastEdited = ""
newSpecFail = "Unable to makespec %s" % lastEdited
switchSpecFail = "Unable to convert the %s" % lastEdited
buildFail = "Unable to build the %s file" % lastEdited

class MakespecTest(unittest.TestCase):
    def setUp(self):
        """
        Init the spec files used for tests
        """
        res = makespec(SCRIPT_FOR_TESTS, "spec_od")
        self.assertEqual(res, 0, newSpecFail)
        res = makespec(SCRIPT_FOR_TESTS, "spec_of", "--onefile")
        self.assertEqual(res, 0, newSpecFail)

    def tearDown(self):
        """\
        Cleaning tests resouces
        """
        self.shortDescription()
        for clean in CLEANUP:
            clean = glob.glob(clean)
            for path in clean:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

    def test_build_onedir(self):
        """\
        Building onedir spec deployment
        """
        self.shortDescription()
        res = self.build("spec_od.spec")
        self.assertEqual(build(res, 0, buildFail)

    def test_build_onefile(self):
        """\
        Building onefile spec deployment
        """
        self.shortDescription()
        res = self.build("spec_of.spec")
        self.assertEqual(build(res, 0, buildFail)

    def test_switch_to_onedir(self):
        """\
        Switching a spec file from onefile to onedir deployment
        """
        self.shortDescription()
        res = self.makespec("spec_of.spec", "_spec_od")
        self.assertEqual(res, 0, switchSpecFail)

        res = self.build("_spec_od.spec")
        self.assertEqual(res, 0, buildFail)

    def test_switch_to_onefile(self):
        """\
        Switching a spec file from onedir to onefile deployment
        """
        self.shortDescription()
        res = self.makespec("spec_of.spec", "_spec_od", "--onefile")
        self.assertEqual(res, 0, switchSpecFail)

        res = self.build("_spec_of.spec")
        self.assertEqual(res, 0, buildFail)

    def test_spec_edit(self):
        """\
        Building an edited spec (try to edit to_edit.spec manually first)
        """
        self.shortDescription()
        # edit the to_edit.spec file before running this test
        if not os.path.isfile(os.path.join(MST_DIR, "to_edit.spec")):
            res = self.makespec(SCRIPT_FOR_TESTS, "to_edit")
            self.assertEqual(res, 0, newSpecFail)
        else:
            res = self.build("to_edit.spec")
            self.assertEqual(res, 0, buildFail)

    def test_switch_edited_file(self):
        """\
        Switching an edited spec file
        """
        self.shortDescription()
        if not os.path.isfile(os.path.join(MST_DIR, "to_edit.spec")):
            res = self.makespec(SCRIPT_FOR_TESTS, "to_edit")
            self.assertEqual(res, 0, newSpecFail)
        else:
            res = self.makespec("to_edit.spec", "to_edit", "--onefile")
            self.assertEqual(res, 0, switchSpecFail)
            res = self.build("_to_edit.spec")
            self.assertEqual(res, 0, buildFail)

    def build(specfile):
        lastEdited = specfile
        return os.system("%s -y %s" % (BUILD_EXE, specfile))

    def makespec(scriptfile, newscriptname = None, dep_mode = "--onedir"):
        lastEdited = scriptfile
        name, _ = os.path.splitext(scriptfile)
        if newscriptname == None:
            newscriptname = name
        return os.system("%s -n %s %s %s" % (MAKESPEC_EXE, newscriptname, dep_mode, scriptfile))

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(MakespecTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
