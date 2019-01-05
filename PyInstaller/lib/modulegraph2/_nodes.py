import dataclasses
import pathlib
from typing import Optional, List, Set

from ._packages import PyPIDistribution


@dataclasses.dataclass
class BaseNode:
    name: str
    loader: Optional[object]
    distribution: Optional[PyPIDistribution]
    filename: pathlib.Path

    # 3th party attribubtes, not used by modulegraph
    extension_attributes: dict

    # XXX: For altgraph, to be removed...
    @property
    def identifier(self):
        return self.name


@dataclasses.dataclass
class Script(BaseNode):
    pass

@dataclasses.dataclass
class Module(BaseNode):
    globals_written: Set[str]
    globals_read: Set[str]

    @property
    def uses_dunder_import(self):
        return '__import__' in self.globals_read

    @property
    def uses_dunder_file(self):
        return '__file__' in self.globals_read

class SourceModule(Module):
    pass

class BytecodeModule(Module):
    pass

class ExtensionModule(Module):
    pass


@dataclasses.dataclass
class NamespacePackage(BaseNode):
    search_path: List[str]

    has_data_files: bool


@dataclasses.dataclass
class Package(BaseNode):
    init_module: BaseNode
    search_path: List[pathlib.Path]
    has_data_files: bool
