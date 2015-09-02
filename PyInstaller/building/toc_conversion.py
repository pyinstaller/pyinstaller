#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import pkg_resources
from ..depend.utils import get_path_to_egg

class DependencyProcessor(object):
    """
    Class to convert final module dependency graph into TOC data structures.
    TOC data structures are suitable for creating the final executable.
    """
    def __init__(self, graph, additional_files):
        self._binaries = set()
        self._datas = set()
        self._distributions = set()
        self.__seen_distribution_paths = set()
        # Include files that were found by hooks.
        # graph.flatten() should include only those modules that are reachable
        # from top-level script.
        for node in graph.flatten(start=graph._top_script_node):
            # Update 'binaries', 'datas'
            name = node.identifier
            if name in additional_files:
                self._binaries.update(additional_files.binaries(name))
                self._datas.update(additional_files.datas(name))
            # Any module can belong to a single distribution
            self._distributions.update(self._get_distribution_for_node(node))


    def _get_distribution_for_node(self, node):
        """Get the distribution a module belongs to.

        Bug: This currently only handles packages in eggs.
        """
        # TODO add support for single modules in eggs (e.g. mock-1.0.1)
        # TODO add support for egg-info:
        # TODO add support for wheels (dist-info)
        #
        # TODO add support for unpacked eggs and for new .whl packages.
        # Wheels:
        #  .../site-packages/pip/  # It seams this has to be a package
        #  .../site-packages/pip-6.1.1.dist-info
        # Unzipped Eggs:
        #  .../site-packages/mock.py   # this may be a single module, too!
        #  .../site-packages/mock-1.0.1-py2.7.egg-info
        # Unzipped Eggs (I asume: multiple-versions externaly managed):
        #  .../site-packages/pyPdf-1.13-py2.6.egg/pyPdf/
        #  .../site-packages/pyPdf-1.13-py2.6.egg/EGG_INFO
        # Zipped Egg:
        #  .../site-packages/zipped.egg/zipped_egg/
        #  .../site-packages/zipped.egg/EGG_INFO
        modpath = node.filename
        if not modpath:
            # e.g. namespace-package
            return []
        # TODO: add other ways to get a distribution path
        distpath = get_path_to_egg(modpath)
        if not distpath or distpath in self.__seen_distribution_paths:
            # no egg or already handled
            return []
        self.__seen_distribution_paths.add(distpath)
        dists = list(pkg_resources.find_distributions(distpath))
        assert len(dists) == 1
        return dists


    # Public methods.

    def make_binaries_toc(self):
        # TODO create a real TOC when handling of more files is added.
        return [(x, y, 'BINARY') for x, y in self._binaries]

    def make_datas_toc(self):
        # TODO create a real TOC when handling of more files is added.
        return [(x, y, 'DATA') for x, y in self._datas]

