"""
Tools for building the module graph

XXX: How to avoid circular dependencies with type checking?
"""
import os
import ast
import pathlib
from typing import Tuple, Iterable, List
import importlib.machinery
from ._nodes import BaseNode, NamespacePackage, ExtensionModule, SourceModule, BytecodeModule, Package
from ._packages import distribution_for_file
from ._bytecode_tools import extract_bytecode_info
from ._ast_tools import extract_ast_info

def _contains_datafiles(directory: pathlib.Path):
    # This is a recursive algorithm, but should be safe...
    for p in directory.parent.iterdir():
        if any(p.name.endswith(sfx) for sfx in importlib.machinery.all_suffixes()):
            # Python module is not a data file
            continue

        elif p.is_dir():
            return _contains_datafiles(p)

        else:
            return True

    return False

def node_for_spec(spec: importlib.machinery.ModuleSpec, path: List[str]) -> Tuple[BaseNode, Iterable[object]]:
    """
    Create the node for a ModuleSpec and locate related imports
    """
    # XXX:
    # - Sources not in filesystem (for example zipfile)
    # - Packages
    # - Setuptools namespace packages

    if spec.loader is None:
        # Namespace package
        # XXX: What about setuptools namespace packages
        node = NamespacePackage(
            name = spec.name,
            loader = spec.loader,
            distribution = None,
            extension_attributes = {},
            filename = pathlib.Path(spec.origin),
            search_path = [pathlib.Path(loc) for loc in spec.submodule_search_locations],
            has_data_files = False,
            )
        return node, ()

    elif isinstance(spec.loader, importlib.machinery.ExtensionFileLoader):
        # XXX: What about a package where __init__ is an extension
        node = ExtensionModule(
            name = spec.name,
            loader = spec.loader,
            distribution = distribution_for_file(spec.origin, path),
            extension_attributes = {},
            filename = pathlib.Path(spec.origin),
            globals_read = set(),
            globals_written = set())
        imports = ()

    elif isinstance(spec.loader, importlib.machinery.SourcelessFileLoader):
        imports, names_written, names_read = extract_bytecode_info(spec.loader.get_code(spec.name))

        node = BytecodeModule(
            name = spec.name,
            loader = spec.loader,
            distribution = distribution_for_file(spec.origin, path),
            extension_attributes = {},
            filename = pathlib.Path(spec.origin),
            globals_written = names_written,
            globals_read = names_read)

    elif isinstance(spec.loader, importlib.machinery.SourceFileLoader):
        source_code = spec.loader.get_source(spec.name)
        if source_code is not None:
            ast_node = compile(source_code, spec.origin, "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)
            ast_imports = extract_ast_info(ast_node)
        else:
            ast_imports = None

        bytecode_imports, names_written, names_read = extract_bytecode_info(spec.loader.get_code(spec.name))

        node = SourceModule(
            name = spec.name,
            loader = spec.loader,
            distribution = distribution_for_file(spec.origin, path),
            extension_attributes = {},
            filename = pathlib.Path(spec.origin),
            globals_written = names_written,
            globals_read = names_read)

        imports = ast_imports if ast_imports is None else bytecode_imports

    else:
        raise RuntimeError(f"Cannot determine node for {spec.name!r} {spec!r}")

    if spec.loader.is_package(spec.name):
        package = Package(
            name = node.name,
            loader = node.loader,
            distribution = node.distribution,
            extension_attributes = {},
            filename = node.filename.parent,
            init_module = node,
            search_path = [node.filename.parent],
            has_data_files = _contains_datafiles(node.filename.parent))

        return package, ()

    return node, ()
