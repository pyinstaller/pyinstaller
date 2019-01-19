"""
Tools for building the module graph
"""
import ast
import pathlib
from typing import Tuple, Iterable, List, Type, cast, Optional
import importlib.machinery
import importlib.abc
import zipfile
import zipimport
from ._nodes import (
    BaseNode,
    BuiltinModule,
    NamespacePackage,
    ExtensionModule,
    SourceModule,
    BytecodeModule,
    FrozenModule,
    Package,
)
from ._packages import distribution_for_file
from ._bytecode_tools import extract_bytecode_info
from ._ast_tools import extract_ast_info
from ._importinfo import ImportInfo


def _contains_datafiles(directory: pathlib.Path):
    """
    Returns true iff *directory* is contains package data

    This works both when *directory* is a path on a filesystem
    and when *directory* points into a zipped directory.
    """
    try:
        for p in directory.iterdir():
            if any(p.name.endswith(sfx) for sfx in importlib.machinery.all_suffixes()):
                # Python module is not a data file
                continue

            elif p.name in ("__pycache__", ".hg", ".svn", ".hg"):
                continue

            elif p.is_dir():
                return _contains_datafiles(p)

            else:
                return True

    except NotADirectoryError:
        names: List[str] = []
        while not directory.exists():
            names.insert(0, directory.name)
            directory = directory.parent

        if not zipfile.is_zipfile(directory):
            raise

        path = "/".join(names) + "/"

        with zipfile.ZipFile(directory) as zf:
            for nm in zf.namelist():
                if nm.startswith(path):
                    if any(
                        part in ("__pycache__", ".hg", ".svn", ".hg")
                        for part in nm.split("/")
                    ):
                        continue

                    elif any(
                        nm.endswith(sfx) for sfx in importlib.machinery.all_suffixes()
                    ):
                        continue

                    else:
                        info = zf.getinfo(nm)
                        if info.is_dir():
                            continue

                        return True

    return False


def node_for_spec(
    spec: importlib.machinery.ModuleSpec, path: List[str]
) -> Tuple[BaseNode, Iterable[object]]:
    """
    Create the node for a ModuleSpec and locate related imports
    """
    node: BaseNode
    imports: Iterable[ImportInfo]

    # XXX: spec.loader can be None in older python versions, but isn't on any
    # recent version (which doesn't help with coverage.py reports)
    if spec.loader is None or type(spec.loader).__name__ == "_NamespaceLoader":
        # Implicit namespace package
        # XXX: The test for the class name of the loader is needed because
        # this is a private class in a private module... See Python issue #35673
        search_path = spec.submodule_search_locations
        assert search_path is not None

        node = NamespacePackage(
            name=spec.name,
            loader=spec.loader,
            distribution=None,
            extension_attributes={},
            filename=pathlib.Path(spec.origin) if spec.origin is not None else None,
            search_path=[pathlib.Path(loc) for loc in search_path],
            has_data_files=False,
        )
        return node, ()

    elif spec.loader is importlib.machinery.BuiltinImporter:
        node = BuiltinModule(
            name=spec.name,
            loader=spec.loader,
            distribution=None,
            extension_attributes={},
            filename=None,
            globals_read=set(),
            globals_written=set(),
        )
        imports = ()

    elif isinstance(spec.loader, importlib.machinery.ExtensionFileLoader):
        node = ExtensionModule(
            name=spec.name,
            loader=spec.loader,
            distribution=distribution_for_file(spec.origin, path)
            if spec.origin is not None
            else None,
            extension_attributes={},
            filename=pathlib.Path(spec.origin) if spec.origin is not None else None,
            globals_read=set(),
            globals_written=set(),
        )
        imports = ()

    elif (
        isinstance(spec.loader, (importlib.abc.InspectLoader, zipimport.zipimporter))
        or spec.loader == importlib.machinery.FrozenImporter
    ):
        importlib.abc.InspectLoader.register(zipimport.zipimporter)
        # Zipimporter is mentioned explictly because it fails the type check for
        # InspectLoader even though it implements the interface.
        # Likewise for _frozen_importlib_external._NamespaceLoader
        loader = cast(importlib.abc.InspectLoader, spec.loader)
        source_code = loader.get_source(spec.name)

        ast_imports: Optional[Iterable[ImportInfo]]

        if source_code is not None:
            filename = spec.origin
            assert filename is not None

            ast_node = compile(
                source_code,
                filename,
                "exec",
                flags=ast.PyCF_ONLY_AST,
                dont_inherit=True,
            )
            ast_imports = extract_ast_info(ast_node)
        else:
            ast_imports = None

        code = loader.get_code(spec.name)
        assert code is not None
        bytecode_imports, names_written, names_read = extract_bytecode_info(code)

        node_type: Type[BaseNode]
        if spec.loader == importlib.machinery.FrozenImporter:
            node_type = FrozenModule
        elif source_code is not None:
            node_type = SourceModule
        else:
            node_type = BytecodeModule

        node = node_type(
            name=spec.name,
            loader=spec.loader,
            distribution=distribution_for_file(spec.origin, path)
            if spec.origin is not None
            else None,
            extension_attributes={},
            filename=pathlib.Path(spec.origin) if spec.origin is not None else None,
            globals_written=names_written,
            globals_read=names_read,
        )

        if ast_imports is not None:
            imports = ast_imports
        else:
            imports = bytecode_imports

    # elif type(spec.loader).__name__ == "_SixMetaPathImporter":
    #    # This is the loader from the six project, which does not quite
    #    # conform to the importlib ABCs.
    #    #
    #    # This returns the node for the resolved import, not the actual import.
    #    #
    #    # XXX: This should return a node for the moved-to location (where possible),
    #    # our callers will detect that the name of the node is different than
    #    # the requested name and will create an alias node.
    #    #
    #    # XXX: should this be some kind of extension API, other custom
    #    #      loaders can also be problematic.
    #    raise RuntimeError("Handle six.moves")

    else:
        raise RuntimeError(
            f"Don't known how to handle {spec.loader!r} for {spec.name!r}"
        )  # pragma: nocover

    loader = cast(importlib.abc.InspectLoader, spec.loader)

    if loader.is_package(spec.name):
        node_file = node.filename
        assert node_file is not None

        node_file = node_file.parent

        package = Package(
            name=node.name,
            loader=node.loader,
            distribution=node.distribution,
            extension_attributes={},
            filename=node_file,
            init_module=node,
            search_path=[node_file],
            has_data_files=_contains_datafiles(node_file),
        )

        return package, imports

    return node, imports
