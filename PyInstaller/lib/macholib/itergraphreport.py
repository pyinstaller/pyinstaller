"""
Utilities for creating dot output from a MachOGraph

XXX: need to rewrite this based on altgraph.Dot
"""

from collections import deque
from itertools import imap

__all__ = ['itergraphreport']

def itergraphreport(nodes, describe_edge, name='G'):
    edges = deque()
    nodetoident = {}
    mainedges = set()

    def nodevisitor(node, data, outgoing, incoming):
        return {'label': str(node)}

    def edgevisitor(edge, data, head, tail):
        return {}

    yield 'digraph %s {\n' % (name,)
    attr = dict(rankdir='LR', concentrate='true')
    cpatt  = '%s="%s"'
    for item in attr.iteritems():
        yield '\t%s;\n' % (cpatt % item,)

    # find all packages (subgraphs)
    for (node, data, outgoing, incoming) in nodes:
        nodetoident[node] = getattr(data, 'identifier', node)

    # create sets for subgraph, write out descriptions
    for (node, data, outgoing, incoming) in nodes:
        # update edges
        for edge in imap(describe_edge, outgoing):
            edges.append(edge)

        # describe node
        yield '\t"%s" [%s];\n' % (
            node,
            ','.join([
                (cpatt % item) for item in
                nodevisitor(node, data, outgoing, incoming).iteritems()
            ]),
        )

    graph = []

    while edges:
        edge, data, head, tail = edges.popleft()
        if data in ('run_file', 'load_dylib'):
            graph.append((edge, data, head, tail))

    def do_graph(edges, tabs):
        edgestr = tabs + '"%s" -> "%s" [%s];\n'
        # describe edge
        for (edge, data, head, tail) in edges:
            attribs = edgevisitor(edge, data, head, tail)
            yield edgestr % (
                head,
                tail,
                ','.join([(cpatt % item) for item in attribs.iteritems()]),
            )

    for s in do_graph(graph, '\t'):
        yield s

    yield '}\n'
