import dataclasses
import pathlib
import os
import importlib.abc
from typing import Optional, List, Set

from ._packages import PyPIDistribution


@dataclasses.dataclass
class BaseNode:
    name: str
    loader: Optional[importlib.abc.Loader]
    distribution: Optional[PyPIDistribution]
    filename: Optional[pathlib.Path]

    # 3th party attribubtes, not used by modulegraph
    extension_attributes: dict

    @property
    def identifier(self) -> str:
        return self.name


class Script(BaseNode):
    def __init__(self, filename: os.PathLike):
        name = os.fspath(filename)
        path = pathlib.Path(filename).resolve()

        return super().__init__(
            name=name,
            loader=None,
            distribution=None,
            filename=path,
            extension_attributes={},
        )


@dataclasses.dataclass
class Module(BaseNode):
    globals_written: Set[str]
    globals_read: Set[str]

    @property
    def uses_dunder_import(self) -> bool:
        return "__import__" in self.globals_read

    @property
    def uses_dunder_file(self) -> bool:
        return "__file__" in self.globals_read


class SourceModule(Module):
    pass


class FrozenModule(Module):
    pass


class BytecodeModule(Module):
    pass


class ExtensionModule(Module):
    pass


class BuiltinModule(Module):
    pass


@dataclasses.dataclass
class NamespacePackage(BaseNode):
    search_path: List[pathlib.Path]

    has_data_files: bool


@dataclasses.dataclass
class Package(BaseNode):
    init_module: BaseNode
    search_path: List[pathlib.Path]
    has_data_files: bool


class ExcludedModule(BaseNode):
    def __init__(self, module_name):
        return super().__init__(
            name=module_name,
            loader=None,
            distribution=None,
            filename=None,
            extension_attributes={},
        )


class MissingModule(BaseNode):
    def __init__(self, module_name):
        return super().__init__(
            name=module_name,
            loader=None,
            distribution=None,
            filename=None,
            extension_attributes={},
        )


@dataclasses.dataclass(init=False)
class AliasNode(BaseNode):
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
