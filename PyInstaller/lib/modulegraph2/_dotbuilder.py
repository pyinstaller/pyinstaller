""" modulegraph._dotbuilder """
from typing import (
    Callable,
    Dict,
    Iterator,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    Union,
)

from objectgraph import EDGE_TYPE, NODE_TYPE  # , ObjectGraph

from ._modulegraph import ModuleGraph

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
    graph: ModuleGraph,
    format_node: Optional[Callable[[NODE_TYPE], Dict[str, Union[str, int]]]] = None,
    format_edge: Optional[
        Callable[[NODE_TYPE, NODE_TYPE, Set[EDGE_TYPE]], Dict[str, Union[str, int]]]
    ] = None,
    group_nodes: Optional[
        Callable[[ModuleGraph], Iterator[Tuple[str, str, Sequence[NODE_TYPE]]]]
    ] = None,
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

    if group_nodes is not None:
        for idx, (group_name, group_icon, group_items) in enumerate(group_nodes(graph)):
            print(f"subgraph cluster_{idx} {{", file=file)
            print(f'   label = "{group_name}"', file=file)
            print(f"   shape = {group_icon}", file=file)
            print("   style=filled; color=lightgray", file=file)
            for node in group_items:
                print(f'   "{node.identifier}"', file=file)

            print("}", file=file)
            print(file=file)
    print("}", file=file)
