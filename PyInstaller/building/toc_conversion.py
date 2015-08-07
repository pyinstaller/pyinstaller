#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


class DependencyProcessor(object):
    """
    Class to convert final module dependency graph into TOC data structures.
    TOC data structures are suitable for creating the final executable.
    """
    def __init__(self, graph, additional_files):
        self._binaries = set()
        self._datas = set()
        # Include files that were found by hooks.
        # graph.flatten() should include only those modules that are reachable
        # from top-level script.
        for node in graph.flatten(start=graph._top_script_node):
            # Update 'binaries', 'datas'
            name = node.identifier
            if name in additional_files:
                self._binaries.update(additional_files.binaries(name))
                self._datas.update(additional_files.datas(name))

    # Public methods.

    def make_binaries_toc(self):
        # TODO create a real TOC when handling of more files is added.
        return [(x, y, 'BINARY') for x, y in self._binaries]

    def make_datas_toc(self):
        # TODO create a real TOC when handling of more files is added.
        return [(x, y, 'DATA') for x, y in self._datas]

