import unittest

from modulegraph2 import _depinfo as depinfo
from modulegraph2 import _importinfo as importinfo


class TestDepInfo(unittest.TestCase):
    def test_basics(self):
        v = depinfo.DependencyInfo(True, False, False, frozenset())

        self.assertTrue(v.is_optional)
        self.assertFalse(v.is_global)
        self.assertFalse(v.in_fromlist)
        self.assertEqual(v.imported_as, frozenset())
        try:
            hash(v)
        except TypeError:
            self.fail("DependencyInfo not hashable")

    def test_creation(self):
        ii = importinfo.ImportInfo(
            import_module="module",
            import_level=0,
            import_names={},
            star_import=True,
            is_in_function=True,
            is_in_conditional=True,
            is_in_tryexcept=True,
        )

        di = depinfo.from_importinfo(ii, False, None)
        self.assertTrue(di.is_optional)
        self.assertFalse(di.is_global)
        self.assertFalse(di.in_fromlist)
        self.assertEqual(di.imported_as, None)

        ii = importinfo.ImportInfo(
            import_module="module",
            import_level=0,
            import_names={},
            star_import=True,
            is_in_function=False,
            is_in_conditional=True,
            is_in_tryexcept=True,
        )

        di = depinfo.from_importinfo(ii, False, "name")
        self.assertTrue(di.is_optional)
        self.assertTrue(di.is_global)
        self.assertFalse(di.in_fromlist)
        self.assertEqual(di.imported_as, "name")

        ii = importinfo.ImportInfo(
            import_module="module",
            import_level=0,
            import_names={},
            star_import=True,
            is_in_function=False,
            is_in_conditional=False,
            is_in_tryexcept=False,
        )

        di = depinfo.from_importinfo(ii, False, "name")
        self.assertFalse(di.is_optional)
        self.assertTrue(di.is_global)
        self.assertFalse(di.in_fromlist)
        self.assertEqual(di.imported_as, "name")

        di = depinfo.from_importinfo(ii, True, "name")
        self.assertFalse(di.is_optional)
        self.assertTrue(di.is_global)
        self.assertTrue(di.in_fromlist)
        self.assertEqual(di.imported_as, "name")
