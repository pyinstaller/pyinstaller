"""
Support code that deals with SWIG.
"""
import importlib.util
import sys
from typing import Optional

import modulegraph2

from ._graphbuilder import node_for_spec
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
    graph: "modulegraph2.ModuleGraph",
    importing_module: Optional[BaseNode],
    missing_name: str,
) -> Optional[BaseNode]:
    if importing_module is None:
        return None

    if missing_name != "_" + importing_module.name.rpartition(".")[-1]:
        return None

    if "swig_import_helper" not in importing_module.globals_written:
        return None

    # This may well be a SWIG extension, try to locate the extension
    # and if found add it as the global module it is (even if found at
    # a non-standard location)
    spec = importlib.util.find_spec("." + missing_name, importing_module.name.rpartition(".")[0])
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
