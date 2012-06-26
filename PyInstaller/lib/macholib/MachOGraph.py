"""
Utilities for reading and writing Mach-O headers
"""

import os
import sys

from altgraph.Graph import Graph
from altgraph.ObjectGraph import ObjectGraph

from macholib.mach_o import *
from macholib.dyld import dyld_find
from macholib.MachO import MachO
from macholib.itergraphreport import itergraphreport

__all__ = ['MachOGraph']

class MissingMachO(object):
    def __init__(self, filename):
        self.graphident = filename
        self.headers = ()

    def __repr__(self):
        return '<%s graphident=%r>' % (type(self).__name__, self.graphident)

class MachOGraph(ObjectGraph):
    """
    Graph data structure of Mach-O dependencies
    """
    def __init__(self, debug=0, graph=None, env=None, executable_path=None):
        super(MachOGraph, self).__init__(debug=debug, graph=graph)
        self.env = env
        self.trans_table = {}
        self.executable_path = executable_path

    def locate(self, filename):
        assert isinstance(filename, (str, unicode))
        fn = self.trans_table.get(filename)
        if fn is None:
            try:
                fn = dyld_find(filename, env=self.env,
                    executable_path=self.executable_path)
                self.trans_table[filename] = fn
            except ValueError:
                return None
        return fn

    def findNode(self, name):
        assert isinstance(name, (str, unicode))
        data = super(MachOGraph, self).findNode(name)
        if data is not None:
            return data
        newname = self.locate(name)
        if newname is not None and newname != name:
            return self.findNode(newname)
        return None

    def run_file(self, pathname, caller=None):
        assert isinstance(pathname, (str, unicode))
        self.msgin(2, "run_file", pathname)
        m = self.findNode(pathname)
        if m is None:
            if not os.path.exists(pathname):
                raise ValueError('%r does not exist' % (pathname,))
            m = self.createNode(MachO, pathname)
            self.createReference(caller, m, edge_data='run_file')
            self.scan_node(m)
        self.msgout(2, '')
        return m

    def load_file(self, name, caller=None):
        assert isinstance(name, (str, unicode))
        self.msgin(2, "load_file", name)
        m = self.findNode(name)
        if m is None:
            newname = self.locate(name)
            if newname is not None and newname != name:
                return self.load_file(newname, caller=caller)
            if os.path.exists(name):
                m = self.createNode(MachO, name)
                self.scan_node(m)
            else:
                m = self.createNode(MissingMachO, name)
        self.msgout(2, '')
        return m

    def scan_node(self, node):
        self.msgin(2, 'scan_node', node)
        for header in node.headers:
            for idx, name, filename in header.walkRelocatables():
                assert isinstance(name, (str, unicode))
                assert isinstance(filename, (str, unicode))
                m = self.load_file(filename, caller=node)
                self.createReference(node, m, edge_data=name)
        self.msgout(2, '', node)

    def itergraphreport(self, name='G'):
        nodes = map(self.graph.describe_node, self.graph.iterdfs(self))
        describe_edge = self.graph.describe_edge
        return itergraphreport(nodes, describe_edge, name=name)

    def graphreport(self, fileobj=None):
        if fileobj is None:
            fileobj = sys.stdout
        fileobj.writelines(self.itergraphreport())

def main(args):
    g = MachOGraph()
    for arg in args:
        g.run_file(arg)
    g.graphreport()

if __name__ == '__main__':
    main(sys.argv[1:] or ['/bin/ls'])
