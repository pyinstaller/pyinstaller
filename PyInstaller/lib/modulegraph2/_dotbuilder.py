"""
modulegraph._dotbuilder
"""
from typing import TypeVar, Callable, Dict, Callable, Any, TextIO
from ._objectgraph import ObjectGraph, T

# - Generic builder for ObjectGraph
# - Using D3.js
# - Enable using custom attributes for nodes and edges
# - Also tabular output?
# - Should reduce the need for a graphviz output


def export_to_dot(
    graph: ObjectGraph[T],
    format_node: Callable[[T], Dict],
    format_edge: Callable[[Any], Dict],
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
