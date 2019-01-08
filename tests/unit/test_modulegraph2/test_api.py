import unittest

import modulegraph2

PUBLIC_SYMBOLS = {
    "DependencyInfo",
    "BuiltinModule",
    "BytecodeModule",
    "ExtensionModule",
    "FrozenModule",
    "MissingModule",
    "Module",
    "ModuleGraph",
    "NamespacePackage",
    "ObjectGraph",
    "Package",
    "PyPIDistribution",
    "Script",
    "SourceModule",
}

PYTHON_SYMBOLS = {
    "__loader__",
    "__doc__",
    "__file__",
    "__builtins__",
    "__spec__",
    "__all__",
    "__name__",
    "__path__",
    "__package__",
    "__cached__",
    "__version__",
}


def submodules(module):
    for nm in dir(module):
        if nm.startswith("_") and isinstance(getattr(module, nm), type(module)):
            yield nm


class TestAPI(unittest.TestCase):
    def test_package_symbols(self):
        self.assertEqual(PUBLIC_SYMBOLS, set(modulegraph2.__all__))
        self.assertEqual(
            PUBLIC_SYMBOLS,
            set(modulegraph2.__dict__.keys())
            - PYTHON_SYMBOLS
            - set(submodules(modulegraph2)),
        )

    def test_all(self):
        for nm in modulegraph2.__all__:
            getattr(modulegraph2, nm)
