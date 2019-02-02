"""
Support code for generating HTML output from a module graph

.. note::
    This module is fairly experimental at this point. At some time
    a generic version of this module will be added to the objectgraph
    package, with modulegraph2 specific functionality in this module.
"""
import operator
import textwrap
from typing import TextIO

from . import BaseNode, ModuleGraph

HTML_PREFIX = textwrap.dedent(
    """\
    <HTML>
      <HEAD>
       <TITLE>Modulegraph report</TITLE>
      </HEAD>
      <BODY>
       <H1>Modulegraph report</H1>
    """
)

HTML_SUFFIX = textwrap.dedent(
    """\
      </BODY>
    </HTML>
    """
)


def export_to_html(file: TextIO, graph: ModuleGraph) -> None:
    """
    Write an HTML version of the *graph* to *fp*".

    The arguments "format_node" and "format_edge" specify
    callbacks to format nodes and edges that are generated.

    These return dict with following keys (all optional):
    - ...
    """

    file.write(HTML_PREFIX)

    reachable = {node.identifier for node in graph.iter_graph()}

    for node in sorted(graph.iter_graph(), key=operator.attrgetter("identifier")):
        if not isinstance(node, BaseNode):
            continue

        print(
            f'<a name="{node.identifier}"><h2>{type(node).__name__} {node.name}</h2></a>',  # noqa:E501
            file=file,
        )
        outgoing = list(graph.outgoing(node))
        if outgoing:
            print("<p>Depends on:", file=file)
            print(
                ", ".join(
                    f'<a href="#{target.identifier}">{target.name}</a>'
                    for _, target in outgoing
                ),
                file=file,
            )

        incoming = list(graph.incoming(node))
        if incoming:
            print("<p>Used by:", file=file)
            print(
                ", ".join(
                    f'<a href="#{source.identifier}">{source.name}</a>'
                    for _, source in incoming
                    if source.identifier in reachable
                ),
                file=file,
            )

    file.write(HTML_SUFFIX)
