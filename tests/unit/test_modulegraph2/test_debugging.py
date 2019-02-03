import unittest

class TestDebugging (unittest.TestCase):
    def test_dump_information(sef):
        import sys

        print("sys attributes:", dir(sys))

        print("abiflags", getattr(sys, "abiflags"))

        print("implementation", getattr(sys, "implementation"))
