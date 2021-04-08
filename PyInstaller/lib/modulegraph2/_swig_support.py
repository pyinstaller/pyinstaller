"""
Support code that deals with SWIG.
"""
import importlib.util
import os
import sys
from types import ModuleType
from typing import Optional, cast

import modulegraph2

from ._graphbuilder import node_for_spec
from ._nodes import BaseNode, ExtensionModule, Module, Package
from ._utilities import FakePackage

# SWIG uses an absolute import to find an extension
# module located in a package (basically a Python 2
# style implict relative imoprt).
#
# These can be detected as follows:
# - The name of the C extension is the name of
#   the enclosing package prefixed by and underscore
# - The source code for the package contains a function
#   named "swig_import_helper" as well a a comment refering
#   to SWIG.
# - The C extension is always imported from the
#   package __init__.


def swig_missing_hook(
    graph: "modulegraph2.ModuleGraph",
    importing_module: Optional[BaseNode],
    missing_name: str,
) -> Optional[BaseNode]:
    """
    Hook function to be used with
    :meth:`ModuleGraph.add_missing_hook <modulegraph2.ModuleGraph.add_missing_hook>`.

    This hook detects when a module in a package uses SWIG to load
    an extension module in the same package using Python 2-style
    implicit relative imports (that don't work in Python 3).

    Adds this extension module as a global module to the graph, which
    corresponds to the Python 3 semantics of the import statement used
    in the code.
    """
    if importing_module is None or not isinstance(importing_module, (Module, Package)):
        return None

    if missing_name != "_" + importing_module.name.rpartition(".")[-1]:
        return None

    if "swig_import_helper" not in importing_module.globals_written:
        return None

    # This may well be a SWIG extension, try to locate the extension
    # and if found add it as the global module it is (even if found at
    # a non-standard location)
    #
    # If the importing_module is a package the relative import should
    # be done relative to that package, otherwise use the parent
    # package.
    if isinstance(importing_module, Package):
        to_import = importing_module.name
    else:
        to_import = importing_module.name.rpartition(".")[0]

    try:
        spec = importlib.util.find_spec("." + missing_name, to_import)
    except ImportError:
        # Loading the package may fail if there's and error. This
        # code assumes that's due to the invalid import by swig and
        # adjusts sys.modules for that before retrying.
        #
        # The fake entry in sys.modules is removed as soon as possible
        # because the assumption is not generally true and leaving the
        # fake module might cause problems in the generic code dealing
        # with simular problems.
        sp = importlib.util.find_spec(to_import)

        # By this time it must be possible to locate the spec,
        # as we were already passed as proper module node.
        #
        # The origin should be set as well, the ImportError shouldn't
        # happen for implicit namespace packages (which don't have
        # an __init__.py and no origin)
        assert sp is not None
        assert sp.origin is not None

        sys.modules[to_import] = cast(
            ModuleType, FakePackage([sp.origin.rpartition(os.sep)[0]])
        )

        spec = importlib.util.find_spec("." + missing_name, to_import)

        del sys.modules[to_import]

    if spec is not None:
        node, imports = node_for_spec(spec, sys.path)
        if not isinstance(node, ExtensionModule):
            # Not an extension after all.
            return None

        assert imports == (), "Extension modules shouldn't have an import list"

        node.name = missing_name
        node.loader = None
        graph.add_node(node)
        return node

    return None
