import unittest

import modulegraph2
from modulegraph2._modulegraph import split_package, full_name


class TestPrivateUtilities(unittest.TestCase):
    def check_results_equal(self, func, input_values):
        for value, expected in input_values:
            with self.subTest(value):
                self.assertEqual(func(*value), expected)

    def test_split_package(self):
        self.check_results_equal(
            split_package,
            [
                (("toplevel",), (None, "toplevel")),
                (("package.module",), ("package", "module")),
                (("package.subpackage.module",), ("package.subpackage", "module")),
                ((".module",), (".", "module")),
                ((".package.module",), (".package", "module")),
                (("..package.module",), ("..package", "module")),
                (("..package.sub.module",), ("..package.sub", "module")),
            ],
        )

        self.assertRaises(ValueError, split_package, "")

        self.assertRaises(TypeError, split_package, None)
        self.assertRaises(TypeError, split_package, 42)
        self.assertRaises(TypeError, split_package, b"module")

    def test_full_name(self):
        self.check_results_equal(
            full_name,
            [
                (("toplevel", None), ("toplevel")),
                (("toplevel", "package"), ("toplevel")),
                (("package.toplevel", None), ("package.toplevel")),
                (("package.toplevel", "package"), ("package.toplevel")),
                ((".toplevel", "package"), ("package.toplevel")),
                (("..toplevel", "package.subpackage"), ("package.toplevel")),
                (("..sub.toplevel", "package.subpackage"), ("package.sub.toplevel")),
            ],
        )

        self.assertRaises(ValueError, full_name, ".toplevel", None)
        self.assertRaises(ValueError, full_name, "..toplevel", "package")
        self.assertRaises(ValueError, full_name, "...toplevel", "package.sub")
