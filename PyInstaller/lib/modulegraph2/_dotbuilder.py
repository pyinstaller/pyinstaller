"""
Export functions for creating Graphviz files.

.. note::
    This module is fairly experimental at this point. At some time
    a generic version of this module will be added to the objectgraph
    package, with modulegraph2 specific functionality in this module.
"""
from typing import Callable, Dict, Iterator, Sequence, Set, TextIO, Tuple, Union

from objectgraph import EDGE_TYPE, NODE_TYPE  # , ObjectGraph

from ._modulegraph import ModuleGraph


def format_attributes(callable, *args):
    """
    Format the results of *callable* in the format expected
    by Graphviz.
    """
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
    format_node: Callable[[NODE_TYPE], Dict[str, Union[str, int]]],
    format_edge: Callable[
        [NODE_TYPE, NODE_TYPE, Set[EDGE_TYPE]], Dict[str, Union[str, int]]
    ],
    group_nodes: Callable[
        [ModuleGraph], Iterator[Tuple[str, str, Sequence[NODE_TYPE]]]
    ],
) -> None:
    """
    Write an dot (graphviz) version of the *graph* to *fp*".

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
