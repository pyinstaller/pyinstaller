import unittest
import importlib.util

from modulegraph2 import _implies as implies


class TestImplies(unittest.TestCase):
    def assert_valid_imply_value(self, entry):
        if isinstance(entry, implies.Alias):
            return
        elif isinstance(entry, implies.Virtual):
            return
        elif isinstance(entry, tuple):
            for e in entry:
                if not isinstance(e, str):
                    self.fail(f"Value in {entry!r} is not a string")

                spec = importlib.util.find_spec(e)
                if spec is None:
                    self.fail(f"{entry!r} is not a valid module or package")

            return
        elif entry is None:
            return

        else:
            self.fail(f"Invalid type for {entry!r}")

    def test_stdlib_implies(self):
        self.assertTrue(isinstance(implies.STDLIB_IMPLIES, dict))

        for k, v in implies.STDLIB_IMPLIES.items():
            with self.subTest(k):
                self.assertTrue(isinstance(k, str))
                self.assert_valid_imply_value(v)
