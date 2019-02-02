import unittest

# - Create virtual environment (venv, virtualenv)
# - Install minimal stuff
# - Create graph with subprocess in the
#   virtual environment
# - Verify graph structure, primarily
#   check that stdlib nodes refer to stuff
#   in the global installation.
# - Expectation is that a lot of code can
#   be shared between tests.


class TestVirtualEnv(unittest.TestCase):
    # Virtualenv from PyPI
    def test_missing(self):
        self.fail()


class TestVenv(unittest.TestCase):
    # Venv from stdlib
    def test_missing(self):
        self.fail()
