import dataclasses
import pathlib
from typing import List


@dataclasses.dataclass
class BaseNode:
    name: str
    loader: object

    # 3th party attribubtes, not used by modulegraph
    extension_attributes: dict = dataclasses.field(default_factory=dict, init=False)

    # XXX: For altgraph, to be removed...
    @property
    def identifier(self):
        return self.name


@dataclasses.dataclass
class Script(BaseNode):
    path: pathlib.Path


@dataclasses.dataclass
class Module(BaseNode):
    path: pathlib.Path
    global_names: set

    uses_dunder_import: bool
    uses_dunder_file: bool


@dataclasses.dataclass
class NamespacePackage(BaseNode):
    search_path: List[str]

    has_data_files: bool


@dataclasses.dataclass
class Package(BaseNode):
    init_module: BaseNode
    search_path: List[str]

    uses_dunder_import: bool
    uses_dunder_file: bool
    has_data_files: bool


@dataclasses.dataclass
class Extension(BaseNode):
    path: pathlib.Path


class InvalidModule(BaseNode):
    pass


class MissingModule(InvalidModule):
    pass
