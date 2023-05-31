import unittest
import encodings
import encodings.aliases
from PyInstaller.lib.modulegraph import util
import sys
import os

try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO

class TestUtil (unittest.TestCase):
    def assertStartsWith(self, a, b, message=None):
        if not a.startswith(b):
            if message is None:
                message = "%r does not start with %r"%(a, b)
            self.fail(message)

    def assertSamePath(self, a, b):
        self.assertStartsWith(os.path.realpath(a), os.path.realpath(b))

    def test_guess_encoding(self):
        fp = BytesIO(b"# coding: utf-8")
        self.assertEqual(util.guess_encoding(fp), "utf-8")

        fp = BytesIO(b"\n# coding: utf-8")
        self.assertEqual(util.guess_encoding(fp), "utf-8")

        fp = BytesIO(b"# coding: latin-1")
        self.assertEqual(util.guess_encoding(fp), "latin-1")

        fp = BytesIO(b"\n# coding: latin-1")
        self.assertEqual(util.guess_encoding(fp), "latin-1")

        fp = BytesIO(b"#!/usr/bin/env/python\n# vim: set fileencoding=latin-1 :")
        self.assertEqual(util.guess_encoding(fp), "latin-1")

        fp = BytesIO(b"\n\n\n# coding: latin-1")
        if sys.version_info[0] == 2:
            self.assertEqual(util.guess_encoding(fp), "ascii")
        else:
            self.assertEqual(util.guess_encoding(fp), "utf-8")

        del fp


if __name__ == "__main__":
    unittest.main()
