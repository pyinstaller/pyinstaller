"""
Commandline interface

- Generate graph from one or more modules/scripts
- Export graph as:
    - HTML
    - dotfile
    - table
- Should be minimal wrapper around other functionality
  to make testing easier.
- It should be possible to condense the graph, for example
  by collapsing (stdlib) packages and PyPI distributions
- For dot export: find a usable layout algoritm and
  make that the default (with option to override)
- Need command-line arguments

XXX: Current code is a crude hack and needs to be split
     into packages.
"""
import os
import pathlib
import sys

from ._dotbuilder import export_to_dot
from ._modulegraph import ModuleGraph

NODE_ATTR = {
    "Script": {"shape": "note"},
    "Package": {"shape": "folder"},
    "SourceModule": {"shape": "rectangle"},
    "BytecodeModule": {"shape": "rectangle"},
    "ExtensionModule": {"shape": "parallelogram"},
    "BuiltinModule": {"shape": "hexagon"},
    "MissingModule": {"shape": "rectangle", "color": "red"},
}


mg = ModuleGraph()
mg.add_script(pathlib.Path("demo.py"))


def format_node(node):
    results = {}
    if node in mg.roots():
        results["penwidth"] = 2
        results["root"] = "true"

    results.update(NODE_ATTR.get(type(node).__name__, {}))

    return results


def format_edge(source, target, edge):
    results = {}

    if all(e.is_optional for e in edge):
        results["style"] = "dashed"

    if source.identifier.startswith(target.identifier + "."):
        results["weight"] = 10
        results["arrowhead"] = "none"

    return results


def group_nodes(graph):
    clusters = {}
    for node in graph.iter_graph():
        if node.distribution is not None:
            dist = node.distribution.name
            if dist not in clusters:
                clusters[dist] = (dist, "tab", [])

            clusters[dist][-1].append(node)

        elif "." in node.identifier and node.filename is not None:
            p = os.fspath(node.filename)
            if "site-packages" not in p and p.startswith(sys.prefix):
                dist = f"stdlib @ {node.name.split('.')[0]}"
                if dist not in clusters:
                    clusters[dist] = (dist, "tab", [])

                clusters[dist][-1].append(node)

    return list(clusters.values())


export_to_dot(sys.stdout, mg, format_node, format_edge, group_nodes)

# XXX: Add proper command-line interface
# - Options for affecting sys.path
# - Option for add_excludes
# - Option for add_implies
# - Option for disabling default implies
# - Options for adding root nodes (add_module and add_script)
# - Options for compressing the graph (replace packages/distributions by single nodes)
# - Options for setting the output format (html, dot, 'report')
# - Options for setting the output location (stdout or file)
