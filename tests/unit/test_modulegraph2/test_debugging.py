import unittest


class TestDebugging(unittest.TestCase):
    def test_dump_information(sef):
        import sys

        print("sys attributes:", dir(sys), file=sys.stderr)

        print("abiflags", getattr(sys, "abiflags"), file=sys.stderr)

        print("implementation", getattr(sys, "implementation"), file=sys.stderr)

        print("modules", list(sys.modules.keys()))
