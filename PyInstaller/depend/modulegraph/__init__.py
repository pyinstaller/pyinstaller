#-----------------------------------------------------------------------------
# Copyright (c) 2005-2026, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
PyInstaller's in-tree module graph.

Public API::

    from PyInstaller.depend.modulegraph import ModuleGraph, Node, ModuleType

``ModuleGraph`` is the single graph class (engine + PyInstaller hook
machinery); ``Node`` and ``ModuleType`` are its data model, and ``Alias`` /
``QueueItem`` support the engine and hook API objects respectively. See the
submodules' docstrings for the full walk-through:

* :mod:`.nodes`  -- the data model (nodes, node types, classification sets)
* :mod:`.graph`  -- the resolution engine and the analysis queue
* :mod:`.hooks`  -- PyInstaller hook machinery, TOC generation
* :mod:`.implies`-- the curated implicit-dependency mapping
"""

from PyInstaller.depend.modulegraph.graph import ModuleGraph, initialize_modgraph
from PyInstaller.depend.modulegraph.implies import get_implies
from PyInstaller.depend.modulegraph.nodes import (
    ALL_MODULE_TYPES,
    BAD_MODULE_TYPES,
    BINARY_MODULE_TYPES,
    MODULE_TYPES_TO_TOC_DICT,
    PURE_PYTHON_MODULE_TYPES,
    SPECIAL_MODULE_TYPES,
    VALID_MODULE_TYPES,
    Alias,
    ModuleType,
    Node,
    QueueItem,
)

__all__ = [
    'ModuleGraph',
    'initialize_modgraph',
    'Node',
    'ModuleType',
    'Alias',
    'QueueItem',
    'get_implies',
    'ALL_MODULE_TYPES',
    'BAD_MODULE_TYPES',
    'BINARY_MODULE_TYPES',
    'MODULE_TYPES_TO_TOC_DICT',
    'PURE_PYTHON_MODULE_TYPES',
    'SPECIAL_MODULE_TYPES',
    'VALID_MODULE_TYPES',
]
