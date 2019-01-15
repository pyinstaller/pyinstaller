"""
modulegraph._dotbuilder
"""
from typing import Callable, Dict, TextIO
from ._objectgraph import ObjectGraph, NODE_TYPE, EDGE_TYPE

# - Generic builder for ObjectGraph
# - Using D3.js
# - Enable using custom attributes for nodes and edges
# - Also tabular output?
# - Should reduce the need for a graphviz output


def export_to_dot(
    graph: ObjectGraph[NODE_TYPE, EDGE_TYPE],
    format_node: Callable[[NODE_TYPE], Dict],
    format_edge: Callable[[EDGE_TYPE], Dict],
    fp: TextIO,
) -> None:
    """
    Write an dot (graphviz) version of the *graph* to *fp".

    The arguments "format_node" and "format_edge" specify
    callbacks to format nodes and edges that are generated.

    These return dict with following keys (all optional):
    - ...
    """
    pass
