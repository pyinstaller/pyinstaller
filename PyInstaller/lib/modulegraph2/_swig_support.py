"""
Support code that deals with SWIG.
"""
import importlib.util
import sys
from typing import Optional

from ._graphbuilder import node_for_spec
from ._modulegraph import ModuleGraph
from ._nodes import BaseNode, ExtensionModule, Package

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
    graph: ModuleGraph, importing_module: Optional[BaseNode], missing_name: str
) -> Optional[BaseNode]:
    if importing_module is None or not isinstance(importing_module, Package):
        return None

    if missing_name != "_" + importing_module.name.rpartition(".")[-1]:
        return None

    if "swig_import_helper" not in importing_module.globals_written:
        return None

    # This may well be a SWIG extension, try to locate the extension
    # and if found add it as the global module it is (even if found at
    # a non-standard location)
    spec = importlib.util.find_spec("." + missing_name, importing_module.name)
    if spec is not None:
        node = node_for_spec(spec, sys.path)
        if not isinstance(node, ExtensionModule):
            # Not an extension after all.
            return None

        node.name = missing_name
        node.loader = None
        graph.add_node(node)
        return node

    return None
