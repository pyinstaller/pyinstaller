#!/usr/bin/env python
import glob
import os, sys
import shutil
import unittest

MST_DIR = os.path.abspath(os.path.split(sys.argv[0])[0])
HOME = os.path.normpath(os.path.join(MST_DIR, ".."))
MAKESPEC_EXE = os.path.join(HOME, "Makespec.py")
BUILD_EXE = os.path.join(HOME, "Build.py")
SCRIPT_FOR_TEST = os.path.join(MST_DIR, "script_for_tests.py")
CLEANUP = """python_exe.build
logdict*.log
warn*.txt
*.py[co]
*/*.py[co]
*/*/*.py[co]
*_od.spec
*_of.spec
build/
dist/
""".split()
newSpecFail = "Unable to makespec %s"
switchSpecFail = "Unable to convert the %s"
buildFail = "Unable to build the %s file"

class MakespecTest(unittest.TestCase):
    def setUp(self):
        """
        Init the spec files used for tests
        """
        self.assertEqual(os.system("%s -n spec_od --onedir %s" % (MAKESPEC_EXE, SCRIPT_FOR_TEST)), 0,
            newSpecFail % SCRIPT_FOR_TEST)
        self.assertEqual(os.system("%s -n spec_of --onefile %s" % (MAKESPEC_EXE, SCRIPT_FOR_TEST)), 0,
            newSpecFail % SCRIPT_FOR_TEST)

    def tearDown(self):
        """\
        Cleaning tests resouces
        """
        self.shortDescription()
        for clean in CLEANUP:
            clean = glob.glob(clean)
            for path in clean:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except OSError, e:
                    print e

    def test_build_onedir(self):
        """\
        Building onedir spec deployment
        """
        self.shortDescription()
        self.assertEqual(os.system("%s -y spec_od.spec" % BUILD_EXE), 0,
            buildFail % "spec_od.spec")

    def test_build_onefile(self):
        """\
        Building onefile spec deployment
        """
        self.shortDescription()
        self.assertEqual(os.system("%s -y spec_of.spec" % BUILD_EXE), 0,
            buildFail % "spec_of.spec")

    def test_switch_to_onedir(self):
        """\
        Switching a spec file from onefile to onedir deployment
        """
        self.shortDescription()
        self.assertEqual(os.system("%s -n _spec_od --onedir spec_of.spec" % MAKESPEC_EXE), 0,
            switchSpecFail % "spec_of.spec")
        self.assertEqual(os.system("%s -y _spec_od.spec" % BUILD_EXE), 0,
            buildFail % "_spec_od.spec")

    def test_switch_to_onefile(self):
        """\
        Switching a spec file from onedir to onefile deployment
        """
        self.shortDescription()
        self.assertEqual(os.system("%s -n _spec_of --onefile spec_od.spec" % MAKESPEC_EXE), 0,
            switchSpecFail % "spec_od.spec")
        self.assertEqual(os.system("%s -y _spec_of.spec" % BUILD_EXE), 0,
            buildFail % "_spec_of.spec")

    def test_spec_edit(self):
        """\
        Building an edited spec (try to edit to_edit.spec manually first)
        """
        self.shortDescription()
        # edit the to_edit.spec file before running this test
        if not os.path.isfile(os.path.join(MST_DIR, "to_edit.spec")):
            self.assertEqual(os.system("%s -n to_edit %s" % (MAKESPEC_EXE, SCRIPT_FOR_TEST)), 0,
                newSpecFail % SCRIPT_FOR_TEST)
        else:
            self.assertEqual(os.system("%s -y to_edit.spec" % BUILD_EXE), 0,
                buildFail % "to_edit.spec")

    def test_switch_edited_file(self):
        """\
        Switching an edited spec file
        """
        self.shortDescription()
        if not os.path.isfile(os.path.join(MST_DIR, "to_edit.spec")):
            self.assertEqual(os.system("%s -n to_edit %s" % (MAKESPEC_EXE, SCRIPT_FOR_TEST)), 0,
                newSpecFail % SCRIPT_FOR_TEST)
        else:
            self.assertEqual(os.system("%s -n _to_edit --onefile to_edit.spec" % MAKESPEC_EXE), 0,
                switchSpecFail % "to_edit.spec")
            self.assertEqual(os.system("%s -y _to_edit.spec" % BUILD_EXE), 0,
                buildFail % "_to_edit.spec")

if __name__ == "__main__":
    unittest.main()
