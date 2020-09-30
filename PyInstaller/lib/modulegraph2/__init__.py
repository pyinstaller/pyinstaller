"""
A module import dependency graph for Python projects.

This package defines a class representing the
dependency graph between a collection of python
modules and scripts, as well as supporting functions
and classes.

The graph itself is an subclass of :class:`objectgraph.ObjectGraph`.

This module provides annotation for use with
`Mypy <https://mypy.readthedocs.io/en/latest/>`_.
"""
__version__ = "2.1"

from ._depinfo import DependencyInfo
from ._distributions import PyPIDistribution, all_distributions, distribution_named
from ._implies import Alias, Virtual
from ._modulegraph import ModuleGraph
from ._nodes import (
    AliasNode,
    BaseNode,
    BuiltinModule,
    BytecodeModule,
    ExcludedModule,
    ExtensionModule,
    FrozenModule,
    InvalidModule,
    InvalidRelativeImport,
    MissingModule,
    Module,
    NamespacePackage,
    Package,
    Script,
    SourceModule,
    VirtualNode,
)
from ._utilities import saved_sys_path

__all__ = (
    "Alias",
    "AliasNode",
    "BaseNode",
    "BuiltinModule",
    "BytecodeModule",
    "DependencyInfo",
    "ExcludedModule",
    "ExtensionModule",
    "FrozenModule",
    "InvalidModule",
    "InvalidRelativeImport",
    "MissingModule",
    "Module",
    "ModuleGraph",
    "NamespacePackage",
    "Package",
    "PyPIDistribution",
    "Script",
    "SourceModule",
    "all_distributions",
    "distribution_named",
    "saved_sys_path",
    "Virtual",
    "VirtualNode",
)
