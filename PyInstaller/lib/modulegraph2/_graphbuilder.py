"""
Tools for building the module graph

XXX: How to avoid circular dependencies with type checking?
"""
import ast
from typing import Tuple, Iterable
import importlib.machinery
from ._nodes import BaseNode, NamespacePackage, ExtensionModule
from ._packages import distribution_for_file
from .bytecode_tools import extract_bytecode_info
from .ast_tools import extract_ast_info

def node_for_spec(module_name: str, spec: importlib.machinery.ModuleSpec) -> Tuple[BaseNode, Iterable[object]]:
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
            name = module_name,
            loader = spec.loader,
            distribution = None,
            filename = spec.origin,
            search_path = spec.submodule_search_locations)
        return node, ()

    elif isinstance(spec.loader, importlib.machinery.ExtensionFileLoader):
        # XXX: What about a package where __init__ is an extension
        node = ExtensionModule(
            name = module_name,
            loader = spec.loader,
            distribution = distribution_for_file(spec.origin),
            filename = spec.origin,
            globals_read = set())
            globals_written = set())
        return node, ()

    elif isinstance(spec.loader, importlib.machinery.SourcelessFileLoader):
        imports, names_written, names_read = extract_bytecode_info(loader.get_code(module_name))

        node = BytecodeModule(
            name = module_name,
            loader = spec.loader,
            distribution = distribution_for_file(spec.origin),
            filename = spec.origin,
            global_written = names_written,
            globals_read = names_read)

        return node, imports

    elif isinstance(spec.loader, importlib.machinery.SourceFileLoader):
        source_code = spec.loader.get_source(module_name)
        if source_code is not None:
            ast_node = compile(source_code, os.fspath(script_path), "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True)
            ast_imports = extract_ast_info(ast_node)
        else:
            ast_imports = None

        bytecode_imports, names_written, names_read = extract_bytecode_info(loader.get_code(module_name))

        node = SourceModule(
            name = module_name,
            loader = spec.loader,
            distribution = distribution_for_file(spec.origin),
            filename = spec.origin,
            global_written = names_written,
            globals_read = names_read)

        return node, ast_imports if ast_imports is None else bytecode_imports

    else:
        raise RuntimeError(f"Cannot determine node for {module_name!r} {spec!r}")
