"""
Tools for building the module graph
"""
import ast
import pathlib
from typing import Tuple, Iterable, List, Sequence
import importlib.machinery
import importlib.abc
import zipfile
from ._nodes import (
    BaseNode,
    NamespacePackage,
    ExtensionModule,
    SourceModule,
    BytecodeModule,
    Package,
)
from ._packages import distribution_for_file
from ._bytecode_tools import extract_bytecode_info
from ._ast_tools import extract_ast_info


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

    except NotADirectoryError as exc:
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
    imports: Sequence  # XXX

    if spec.loader is None or (
        spec.origin is None
        and isinstance(spec.loader, importlib.abc.InspectLoader)
        and spec.loader.get_source(spec.name) == ""
    ):
        # Namespace package
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

    elif isinstance(spec.loader, importlib.abc.InspectLoader):
        source_code = spec.loader.get_source(spec.name)
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
            ast_imports = iter(())

        code = spec.loader.get_code(spec.name)
        assert code is not None
        bytecode_imports, names_written, names_read = extract_bytecode_info(code)

        node_type = SourceModule if source_code is not None else BytecodeModule

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

        imports = ast_imports if ast_imports else bytecode_imports

    else:
        raise RuntimeError(
            f"Don't known how to handle {spec.loader!r} for {spec.name!r}"
        )  # pragma: nocover

    if spec.loader.is_package(spec.name):
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
