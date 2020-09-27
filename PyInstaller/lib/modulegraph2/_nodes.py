import dataclasses
import importlib.abc
import os
import pathlib
from typing import List, Optional, Set

from ._distributions import PyPIDistribution


@dataclasses.dataclass
class BaseNode:
    """
    Base class for all module nodes in the dependency graph.

    Attributes:

      name
        Name of the module.

      loader
        Importlib loader for the module when available.

      distribution
        Package distribution that contains this module.
        :data:`None` for the stdlib and uninstalled modules.

      filename
        Filesystem path to the module when available

      extension_attributes
        A dictionary for use by users for the modulegraph2
        library, not used by modulegraph2 itself.
    """

    name: str
    loader: Optional[importlib.abc.Loader]
    distribution: Optional[PyPIDistribution]
    filename: Optional[pathlib.Path]

    # 3th party attribubtes, not used by modulegraph
    extension_attributes: dict

    @property
    def identifier(self) -> str:
        """
        Graph identifier for use with
        :class:`objectgraph.ObjectGraph`.
        """
        return self.name


@dataclasses.dataclass
class Script(BaseNode):
    """
    Node representing a Python script.

    The name of the node is the string representation
    of the full filename of the script.
    """

    globals_written: Set[str]
    globals_read: Set[str]

    def __init__(self, filename: os.PathLike):
        name = os.fspath(filename)
        path = pathlib.Path(filename).resolve()

        super().__init__(
            name=name,
            loader=None,
            distribution=None,
            filename=path,
            extension_attributes={},
        )
        self.globals_read = set()
        self.globals_written = set()


@dataclasses.dataclass
class Module(BaseNode):
    """
    Information about a Module

    Attributes:
      globals_written
        Set of global names written to by the module

      globals_read
        Set of global names read by the module
    """

    globals_written: Set[str]
    globals_read: Set[str]

    @property
    def uses_dunder_import(self) -> bool:
        """
        True if the module appears to use the
        :func:`__import__` function.
        """
        return "__import__" in self.globals_read

    @property
    def uses_dunder_file(self) -> bool:
        """
        True if the module appears to use the
        ``__file__`` attribute.
        """
        return "__file__" in self.globals_read


class SourceModule(Module):
    """
    Node representing a python module for which
    the source code is available.
    """

    pass


class FrozenModule(Module):
    """
    Note representing a python module that is
    frozen into an executable. This has source
    code available, but not on the filesystem.
    """

    pass


class BytecodeModule(Module):
    """
    Node representing a python module for which
    only byte code is available.
    """

    pass


class ExtensionModule(Module):
    """
    Node representing a native extension module.
    """

    pass


class BuiltinModule(Module):
    """
    Node representing a built-in extension module.
    """

    pass


class InvalidModule(Module):
    """
    Not representing a module that could not be
    loaded due to having invalid syntax.
    """

    pass


@dataclasses.dataclass
class NamespacePackage(BaseNode):
    """
    Node representing an implicit namespace
    package (PEP 420).

    Attributes:
      search_path
        The search path for modules in this
        package.
    """

    search_path: List[pathlib.Path]

    has_data_files: bool

    @property
    def globals_written(self):
        """ Always an empty set """
        return frozenset()

    @property
    def globals_read(self):
        """ Always an empty set """
        return frozenset()


@dataclasses.dataclass
class Package(BaseNode):
    """
    Node representing a namespace
    package with an ``__init__`` module.

    Attributes:
      init_module
        Node representing the ``__init__`` module
        for this package.

      search_path
        The search path for modules in this
        package.

      has_data_files
        True if this package contains data files
        (other than empty directories and python
        files).

      namespace_type
        None, "pkgutil" or "pkg_resources" for
        regular packages, namespace packages using
        pkgutil and namespace packages using pkg_resources.
    """

    init_module: BaseNode
    search_path: List[pathlib.Path]
    has_data_files: bool
    namespace_type: Optional[str]

    @property
    def globals_written(self):
        """ The globals written to by the module __init__ """
        return self.init_module.globals_written

    @property
    def globals_read(self):
        """ The globals read from by the module __init__ """
        return self.init_module.globals_read


class ExcludedModule(BaseNode):
    """
    Node representing a module that is explicitly
    excluded by the user.
    """

    def __init__(self, module_name):
        return super().__init__(
            name=module_name,
            loader=None,
            distribution=None,
            filename=None,
            extension_attributes={},
        )


class MissingModule(BaseNode):
    """
    Node representing a name that is imported, but
    could not be located.
    """

    def __init__(self, module_name):
        return super().__init__(
            name=module_name,
            loader=None,
            distribution=None,
            filename=None,
            extension_attributes={},
        )


class InvalidRelativeImport(BaseNode):
    """
    Node representing a relative import that refers
    to a location outside of a toplevel package.

    The name is a name starting with one or more
    dots.
    """

    def __init__(self, module_name):
        return super().__init__(
            name=module_name,
            loader=None,
            distribution=None,
            filename=None,
            extension_attributes={},
        )


@dataclasses.dataclass(init=False)
class VirtualNode(BaseNode):
    """
    Node representing a virtual module, that is
    added to :data:`sys.modules` by some other
    module.

    Attributes
      providing_module
        The module that creates this module in
        :data:`sys.modules`.
    """

    providing_module: BaseNode

    def __init__(self, module_name, providing_module):
        super().__init__(
            name=module_name,
            loader=None,
            distribution=None,
            filename=None,
            extension_attributes={},
        )
        self.providing_module = providing_module


@dataclasses.dataclass(init=False)
class AliasNode(BaseNode):
    """
    Node representing a module alias, that is an
    imported name that refers to some other module.

    Attributes
      actual_module
        The module that this name aliases to.
    """

    actual_module: BaseNode

    def __init__(self, module_name, actual_module):
        super().__init__(
            name=module_name,
            loader=None,
            distribution=None,
            filename=None,
            extension_attributes={},
        )
        self.actual_module = actual_module
