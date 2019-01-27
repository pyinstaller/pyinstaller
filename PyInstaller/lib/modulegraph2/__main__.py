"""
Commandline interface
"""
import argparse
import contextlib
import enum
import functools
import importlib
import os
import pathlib
import sys
from typing import List, TextIO

from . import __version__
from ._dotbuilder import export_to_dot
from ._htmlbuilder import export_to_html
from ._modulegraph import ModuleGraph

# --- XXX: This block needs to be elsewhere

NODE_ATTR = {
    "Script": {"shape": "note"},
    "Package": {"shape": "folder"},
    "SourceModule": {"shape": "rectangle"},
    "BytecodeModule": {"shape": "rectangle"},
    "ExtensionModule": {"shape": "parallelogram"},
    "BuiltinModule": {"shape": "hexagon"},
    "MissingModule": {"shape": "rectangle", "color": "red"},
}


def format_node(node, mg):
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


# ----


@enum.unique
class NodeType(enum.Enum):
    SCRIPT = enum.auto()
    MODULE = enum.auto()
    DISTRIBUTION = enum.auto()


@enum.unique
class OutputFormat(enum.Enum):
    HTML = "html"
    GRAPHVIZ = "dot"


@contextlib.contextmanager
def saved_syspath():
    orig_path = list(sys.path)

    try:
        yield

    finally:
        sys.path[:] = orig_path
        importlib.invalidate_caches()


def parse_arguments(argv: List[str]) -> argparse.Namespace:
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
    with saved_syspath():
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
        elif args.node_type == NodeType.DISTRIBUTION:  # pragma: nocover
            print("Not supported yet")
            raise SystemExit(2)

        else:  # pragma: nocover
            assert False, "Invalid NodeType"

        return mg


def print_graph(fp: TextIO, output_format: OutputFormat, mg: ModuleGraph) -> None:
    if output_format == OutputFormat.HTML:
        export_to_html(fp, mg)

    elif output_format == OutputFormat.GRAPHVIZ:
        export_to_dot(
            fp, mg, functools.partial(format_node, mg=mg), format_edge, group_nodes
        )

    else:  # pragma: nocover
        assert False, "Invalid OutputFormat"


def format_graph(args: argparse.Namespace, mg: ModuleGraph) -> None:
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
    args = parse_arguments(argv)

    mg = make_graph(args)
    format_graph(args, mg)


if __name__ == "__main__":  # pragma: nocover
    main(sys.argv[1:])
