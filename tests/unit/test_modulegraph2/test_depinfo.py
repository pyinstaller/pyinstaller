import unittest

from modulegraph2 import _depinfo as depinfo


class TestDepInfo(unittest.TestCase):
    def test_basics(self):
        v = depinfo.DependencyInfo(True, False)

        self.assertTrue(v.optional)
        self.assertFalse(v.fromlist)
        try:
            hash(v)
        except TypeError:
            self.fail("DependencyInfo not hashable")

    def test_merging(self):
        for o_opt, u_opt, r_opt in [
            (True, True, True),
            (True, False, False),
            (False, True, False),
            (False, False, False),
        ]:
            for o_fl, u_fl, r_fl in [
                (True, True, True),
                (True, False, False),
                (False, True, False),
                (False, False, False),
            ]:
                with self.subTest(o_opt=o_opt, u_opt=u_opt, o_fl=o_fl, u_fl=u_fl):
                    o = depinfo.DependencyInfo(o_opt, o_fl)
                    u = depinfo.DependencyInfo(u_opt, u_fl)

                    m = depinfo.merged_depinfo(o, u)
                    self.assertIsInstance(m, depinfo.DependencyInfo)
                    self.assertEqual(m.optional, r_opt)
                    self.assertEqual(m.fromlist, r_fl)

        for o_opt, o_fl in [(True, True), (True, False), (False, True), (False, False)]:
            with self.subTest(o_opt=o_opt, o_fl=o_fl, other=None):
                o = depinfo.DependencyInfo(o_opt, o_fl)

                m = depinfo.merged_depinfo(o, None)
                self.assertIsInstance(m, depinfo.DependencyInfo)
                self.assertEqual(m.optional, False)
                self.assertEqual(m.fromlist, o_fl)

                m = depinfo.merged_depinfo(None, o)
                self.assertIsInstance(m, depinfo.DependencyInfo)
                self.assertEqual(m.optional, False)
                self.assertEqual(m.fromlist, o_fl)

        with self.subTest("None, None"):
            m = depinfo.merged_depinfo(None, None)
            self.assertIs(m, None)
