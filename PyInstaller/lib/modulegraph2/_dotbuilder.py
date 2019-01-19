""" modulegraph._dotbuilder """
from typing import Callable, Dict, Optional, TextIO

from ._objectgraph import EDGE_TYPE, NODE_TYPE, ObjectGraph

# - Generic builder for ObjectGraph
# - Using D3.js
# - Enable using custom attributes for nodes and edges
# - Also tabular output?
# - Should reduce the need for a graphviz output


def format_attributes(callable, *args):
    if callable is None:
        return ""

    value = callable(*args)
    if not value:
        return ""

    else:
        parts = []
        for k in sorted(value):
            parts.append(f"{k}={value[k]}")
        return f" [{', '.join(parts)}]"


def export_to_dot(
    file: TextIO,
    graph: ObjectGraph[NODE_TYPE, EDGE_TYPE],
    format_node: Optional[Callable[[NODE_TYPE], Dict]] = None,
    format_edge: Optional[Callable[[NODE_TYPE, NODE_TYPE, EDGE_TYPE], Dict]] = None,
) -> None:
    """
    Write an dot (graphviz) version of the *graph* to *fp".

    The arguments "format_node" and "format_edge" specify
    callbacks to format nodes and edges that are generated.

    These return dict with following keys (all optional):
    - ...
    """
    print("digraph modulegraph {", file=file)

    for source in graph.iter_graph():
        print(
            f'    "{source.identifier}"{format_attributes(format_node, source)}',
            file=file,
        )
        for edge, target in graph.outgoing(source):
            print(
                f'    "{source.identifier}" -> "{target.identifier}"{format_attributes(format_edge, source, target, edge)}',  # noqa: B950
                file=file,
            )
    print("}", file=file)
