"""
Commandline interface
"""
import argparse
import enum
import functools
import sys
from typing import Dict, Iterator, List, Sequence, Set, TextIO, Tuple, Union

from . import __version__
from ._depinfo import DependencyInfo
from ._dotbuilder import export_to_dot
from ._htmlbuilder import export_to_html
from ._modulegraph import ModuleGraph
from ._nodes import BaseNode
from ._utilities import saved_sys_path

# --- Helper code for the Graphviz builder

# Mapping from node class name to Graphviz attributes for the
# node.
NODE_ATTR = {
    "Script": {"shape": "note"},
    "Package": {"shape": "folder"},
    "SourceModule": {"shape": "rectangle"},
    "BytecodeModule": {"shape": "rectangle"},
    "ExtensionModule": {"shape": "parallelogram"},
    "BuiltinModule": {"shape": "hexagon"},
    "MissingModule": {"shape": "rectangle", "color": "red"},
}


def format_node(node: BaseNode, mg: ModuleGraph) -> Dict[str, Union[str, int]]:
    """
    Return a dict of Graphviz attributes for *node*

    Args:
       node: The node to format
       mg: The graph containing the node

    Returns:
       Graphviz attributes for the node
    """
    results: Dict[str, Union[str, int]] = {}
    if node in mg.roots():
        results["penwidth"] = 2
        results["root"] = "true"

    results.update(NODE_ATTR.get(type(node).__name__, {}))

    return results


def format_edge(
    source: BaseNode, target: BaseNode, edge: Set[DependencyInfo]
) -> Dict[str, Union[str, int]]:
    """
    Return a dict of Graphviz attributes for an edge

    Args:
      source: Source node for the edge
      target: Target node for the edge
      edge: Set of edge attributes

    Returns:
       Graphviz attributes for the edge
    """
    results: Dict[str, Union[str, int]] = {}

    if all(e.is_optional for e in edge):
        results["style"] = "dashed"

    if source.identifier.startswith(target.identifier + "."):
        results["weight"] = 10
        results["arrowhead"] = "none"

    return results


def group_nodes(graph: ModuleGraph) -> Iterator[Tuple[str, str, Sequence[BaseNode]]]:
    """
    Detect groups of reachable nodes in the graph.

    This function groups nodes in two ways:
    - Group all nodes related to a particular distribution
    - Group all nodes in the same stdlib package

    Args:
      graph: The dependency graph

    Returns:
      A list of ``(groupname, shape, nodes)`` for the
      groupings.
    """
    clusters: Dict[str, Tuple[str, str, List[BaseNode]]] = {}
    for node in graph.iter_graph():
        if not isinstance(node, BaseNode):
            continue

        if node.distribution is not None:
            dist = node.distribution.name
            if dist not in clusters:
                clusters[dist] = (dist, "tab", [])

            clusters[dist][-1].append(node)

    return iter(clusters.values())


# ----


@enum.unique
class NodeType(enum.Enum):
    """
    The types of nodes that can be added to
    a dependency graph
    """

    SCRIPT = enum.auto()
    MODULE = enum.auto()
    DISTRIBUTION = enum.auto()


@enum.unique
class OutputFormat(enum.Enum):
    """
    The file formats that can be used for
    output.
    """

    HTML = "html"
    GRAPHVIZ = "dot"


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    """
    Parse command-line arguments for the module.

    The result namespace contains the following attributes:

      - **node_type (NodeType)**: The type of node that should be added.

      - **output_format (OutputFormat)**: File type for outputting the graph.

      - **excludes (List[str])**: List of modules to exclude from the graph.

      - **path (List[str])**: Directories to add to :data:`sys.path`.

      - **output_file** (Optional[str])**: Filename to output to.

    Args:
      argv: The script arguments, usually ``sys.argv[1:]``

    Returns:
      The parsed options.

    Raises:
      SystemExit: On usage errors or when the user has requested help
    """
    parser = argparse.ArgumentParser(
        prog=f"{sys.executable.rsplit('/')[-1]} -mmodulegraph2",
        description=f"Graph builder from modulegraph2 {__version__}",
    )
    parser.add_argument(
        "-m",
        "--module",
        action="store_const",
        const=NodeType.MODULE,
        dest="node_type",
        default=NodeType.MODULE,
        help="The positional arguments are modules (the default)",
    )
    parser.add_argument(
        "-s",
        "--script",
        action="store_const",
        const=NodeType.SCRIPT,
        dest="node_type",
        help="The positional arguments are scripts",
    )
    parser.add_argument(
        "-d",
        "--distribution",
        action="store_const",
        const=NodeType.DISTRIBUTION,
        dest="node_type",
        help="The positional arguments are distributions",
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="output_format",
        choices=[v.value for v in OutputFormat],
        default=OutputFormat.HTML.value,
        help="The output format (default: %(default)s)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        dest="excludes",
        action="append",
        metavar="NAME",
        default=[],
        help="Add NAME to the list of module excludes",
    )
    parser.add_argument(
        "-p",
        "--path",
        dest="path",
        action="append",
        metavar="PATH",
        default=[],
        help="Add PATH to the module search path",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        metavar="FILE",
        default=None,
        help="Write output to path (defaults to stdout)",
    )
    parser.add_argument("name", nargs="+", help="Names to add to the graph")
    args = parser.parse_args(argv)

    # Not sure if this can be done cleaner...
    args.output_format = OutputFormat(args.output_format)

    return args


def make_graph(args: argparse.Namespace) -> ModuleGraph:
    """
    Build a dependency graph based on the command-line arguments.

    Args:
      args: The result of :func:`parse_arguments`.

    Returns:
      The generated graph
    """
    with saved_sys_path():
        for p in args.path[::-1]:
            sys.path.insert(0, p)

        mg = ModuleGraph()
        mg.add_excludes(args.excludes)

        if args.node_type == NodeType.MODULE:
            for name in args.name:
                mg.add_module(name)
        elif args.node_type == NodeType.SCRIPT:
            for name in args.name:
                mg.add_script(name)
        elif args.node_type == NodeType.DISTRIBUTION:
            for name in args.name:
                mg.add_distribution(name)

        else:  # pragma: nocover
            raise AssertionError("Invalid NodeType")

        return mg


def print_graph(file: TextIO, output_format: OutputFormat, mg: ModuleGraph) -> None:
    """
    Output the graph in the given output format to a text stream.

    Args:
      file: The text stream to data should be written to

      output_format: The format to use

      mg: The graph to write
    """
    if output_format == OutputFormat.HTML:
        export_to_html(file, mg)

    elif output_format == OutputFormat.GRAPHVIZ:
        export_to_dot(
            file, mg, functools.partial(format_node, mg=mg), format_edge, group_nodes
        )

    else:  # pragma: nocover
        raise AssertionError("Invalid OutputFormat")


def format_graph(args: argparse.Namespace, mg: ModuleGraph) -> None:
    """
    Output the graph as specified in *args*.

    Args:
      args: Command-line arguments

      mg: The graph to output.
    """
    if args.output_file is None:
        print_graph(sys.stdout, args.output_format, mg)
    else:
        try:
            with open(args.output_file, "w") as fp:
                print_graph(fp, args.output_format, mg)

        except OSError as exc:
            print(exc, file=sys.stderr)
            raise SystemExit(1)


def main(argv: List[str]) -> None:
    """
    Entry point for the module.

    Args:
      argv: Command-line arguments, should be ``sys.path[1:]``.
    """
    args = parse_arguments(argv)

    mg = make_graph(args)
    format_graph(args, mg)


if __name__ == "__main__":  # pragma: nocover
    main(sys.argv[1:])
