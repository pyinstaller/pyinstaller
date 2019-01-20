import unittest

import modulegraph2
from modulegraph2._modulegraph import split_package


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
        self.assertRaises(ValueError, split_package, "module..package")
        self.assertRaises(ValueError, split_package, "..")
