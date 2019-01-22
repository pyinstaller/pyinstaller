"""
Support code for generating HTML
output from a graph
"""
import json
import textwrap
from typing import Callable, Dict, Optional, TextIO

from ._objectgraph import EDGE_TYPE, NODE_TYPE, ObjectGraph

# - Generic builder for ObjectGraph
# - Using D3.js
# - Enable using custom attributes for nodes and edges
# - Also tabular output?
# - Should reduce the need for a graphviz output
# - Have a way to expand/collapse python packages
# - Click to show details?
# - See http://visualdataweb.de/webvowl/#

HTML_PREFIX = textwrap.dedent(
    """\
    <HTML>
      <HEAD>
       <TITLE>...<TITLE>
      </HEAD>
      <BODY>
       <H1>...</H1>
    """
)

HTML_SUFFIX = textwrap.dedent(
    """\
      </BODY>
    </HTML>
    """
)


def export_to_html(
    file: TextIO,
    graph: ObjectGraph[NODE_TYPE, EDGE_TYPE],
    format_node: Optional[Callable[[NODE_TYPE], Dict]] = None,
    format_edge: Optional[Callable[[EDGE_TYPE], Dict]] = None,
) -> None:
    """
    Write an HTML version of the *graph* to *fp".

    The arguments "format_node" and "format_edge" specify
    callbacks to format nodes and edges that are generated.

    These return dict with following keys (all optional):
    - ...
    """

    nodes = []
    edges = []

    # XXX: Caller should be able ot affect the JS code in the HTML?
    # XXX: Also write tabular version (like in classic modulegraph)?

    for node in graph.iter_graph():
        # XXX: Use format functions to add formatting info the the data
        #      for nodes and edges
        nodes.append({"id": node.identifier})

        for _, target in graph.outgoing(node):
            edges.append({"source": node.identifier, "target": target.identifier})

    file.write(HTML_PREFIX)

    file.write(json.dumps(nodes))
    file.write(json.dumps(edges))

    file.write(HTML_SUFFIX)
