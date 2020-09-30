"""
Tools for building the module graph
"""
import ast
import importlib.abc
import importlib.machinery
import pathlib
import zipfile
import zipimport
from typing import Iterable, List, Optional, Tuple, Type, cast

from ._ast_tools import extract_ast_info
from ._bytecode_tools import extract_bytecode_info
from ._distributions import distribution_for_file
from ._importinfo import ImportInfo
from ._nodes import (
    BaseNode,
    BuiltinModule,
    BytecodeModule,
    ExtensionModule,
    FrozenModule,
    InvalidModule,
    MissingModule,
    Module,
    NamespacePackage,
    Package,
    SourceModule,
)
from ._virtualenv_support import adjust_path

SIX_MOVES_GLOBALS = {"filter", "input", "map", "range", "xrange", "zip"}

SIX_MOVES_TO = {
    "builtins": "builtins",
    "configparser": "configparser",
    "copyreg": "copyreg",
    "cPickle": "pickle",
    "cStringIO": "io",
    "dbm_gnu": "dbm.gnu",
    "_dummy_thread": "_dummy_thread",
    "email_mime_multipart": "email.mime.multipart",
    "email_mime_nonmultipart": "email.mime.nonmultipart",
    "email_mime_text": "email.mime.text",
    "email_mime_base": "email.mime.base",
    "http_cookiejar": "http.cookiejar",
    "http_cookies": "http.cookies",
    "html_entities": "html.entities",
    "html_parser": "html.parser",
    "http_client": "http.client",
    "BaseHTTPServer": "http.server",
    "CGIHTTPServer": "http.server",
    "SimpleHTTPServer": "http.server",
    "queue": "queue",
    "reprlib": "reprlib",
    "shlex_quote": "shlex",
    "socketserver": "socketserver",
    "_thread": "_thread",
    "tkinter": "tkinter",
    "tkinter_dialog": "tkinter.dialog",
    "tkinter_filedialog": "tkinter.FileDialog",
    "tkinter_scrolledtext": "tkinter.scrolledtext",
    "tkinter_simpledialog": "tkinter.simpledialog",
    "tkinter_ttk": "tkinter.ttk",
    "tkinter_tix": "tkinter.tix",
    "tkinter_constants": "tkinter.constants",
    "tkinter_dnd": "tkinter.dnd",
    "tkinter_colorchooser": "tkinter.colorchooser",
    "tkinter_commondialog": "tkinter.commondialog",
    "tkinter_tkfiledialog": "tkinter.filedialog",
    "tkinter_font": "tkinter.font",
    "tkinter_messagebox": "tkinter.messagebox",
    "tkinter_tksimpledialog": "tkinter.simpledialog",
    "urllib": "urllib",
    "urllib.parse": "urllib.parse",
    "urllib.error": "urllib.error",
    "urllib.request": "urllib.request",
    "urllib.response": "urllib.response",
    "urllib.robotparser": "urllib.robotparser",
    "urllib_robotparser": "urllib.robotparser",
    "UserDict": "collections.UserDict",
    "UserList": "collections.UserList",
    "UserString": "collections.UserString",
    "winreg": "winreg",
    "xmlrpc_client": "xmlrpc.client",
    "xmlrpc_server": "xmlrpc.server",
    # All these are function imports, and don't
    # get found when using find_spec...
    "filterfalse": "itertools",
    "getcwd": "os",
    "getcwdb": "os",
    "intern": "sys",
    "reduce": "functools",
    "reload_module": "importlib",
    "zip_longest": "itertools",
}


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

    except (NotADirectoryError, FileNotFoundError):
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
) -> Tuple[BaseNode, Iterable[ImportInfo]]:
    """
    Create the node for a ModuleSpec and locate related imports
    """
    node: BaseNode
    imports: Iterable[ImportInfo]
    source_code: Optional[str] = None

    loader: Optional[importlib.abc.Loader] = cast(
        Optional[importlib.abc.Loader], spec.loader
    )

    if loader is None or type(loader).__name__ == "_NamespaceLoader":
        # Implicit namespace package
        #
        # The test for the name of the class is needed because the loader
        # for namespace packages is a private class, see python issue #35673.
        search_path = spec.submodule_search_locations
        assert search_path is not None

        node = NamespacePackage(
            name=spec.name,
            loader=loader,
            distribution=None,
            extension_attributes={},
            filename=pathlib.Path(adjust_path(spec.origin))
            if spec.origin is not None
            else None,
            search_path=[pathlib.Path(loc) for loc in search_path],
            has_data_files=False,
        )
        return node, ()

    elif loader is importlib.machinery.BuiltinImporter:
        node = BuiltinModule(
            name=spec.name,
            loader=loader,
            distribution=None,
            extension_attributes={},
            filename=None,
            globals_read=set(),
            globals_written=set(),
        )
        imports = ()

    elif isinstance(loader, importlib.machinery.ExtensionFileLoader):
        node = ExtensionModule(
            name=spec.name,
            loader=loader,
            distribution=distribution_for_file(spec.origin, path)
            if spec.origin is not None
            else None,
            extension_attributes={},
            filename=pathlib.Path(adjust_path(spec.origin))
            if spec.origin is not None
            else None,
            globals_read=set(),
            globals_written=set(),
        )
        imports = ()

    elif (
        isinstance(loader, (importlib.abc.InspectLoader, zipimport.zipimporter))
        or loader == importlib.machinery.FrozenImporter
    ):
        importlib.abc.InspectLoader.register(zipimport.zipimporter)
        # Zipimporter is mentioned explictly because it fails the type check for
        # InspectLoader even though it implements the interface.
        # Likewise for _frozen_importlib_external._NamespaceLoader

        inspect_loader = cast(importlib.abc.InspectLoader, loader)
        source_code = inspect_loader.get_source(spec.name)

        ast_imports: Optional[Iterable[ImportInfo]]
        node_type: Optional[Type[Module]] = None

        if source_code is not None:
            filename = spec.origin
            assert filename is not None

            try:
                ast_node = compile(
                    source_code,
                    filename,
                    "exec",
                    flags=ast.PyCF_ONLY_AST,
                    dont_inherit=True,
                )
            except SyntaxError:
                node_type = InvalidModule
                ast_imports = None

            else:
                ast_imports = extract_ast_info(ast_node)
        else:
            ast_imports = None

        try:
            code = inspect_loader.get_code(spec.name)
            assert code is not None
            bytecode_imports, names_written, names_read = extract_bytecode_info(code)
        except SyntaxError:
            node_type = InvalidModule
            bytecode_imports = []
            names_written = set()
            names_read = set()

        if node_type is None:
            if loader == importlib.machinery.FrozenImporter:
                node_type = FrozenModule
            elif source_code is not None:
                node_type = SourceModule
            else:
                node_type = BytecodeModule

        node = node_type(
            name=spec.name,
            loader=loader,
            distribution=(
                distribution_for_file(spec.origin, path)
                if spec.origin is not None
                and loader != importlib.machinery.FrozenImporter
                else None
            ),
            extension_attributes={},
            filename=(
                pathlib.Path(adjust_path(spec.origin))
                if spec.origin is not None
                and loader != importlib.machinery.FrozenImporter
                else None
            ),
            globals_written=names_written,
            globals_read=names_read,
        )

        if ast_imports is not None:
            imports = ast_imports
        else:
            imports = bytecode_imports

    elif type(loader).__name__ == "_SixMetaPathImporter":
        # This is the loader from the six project, which does not quite
        # conform to the importlib ABCs.
        #
        # This returns the node for the resolved import, not the actual import.

        if spec.name.endswith(".moves"):
            # six.moves itself
            node = Package(
                name=spec.name,
                loader=loader,
                distribution=None,
                extension_attributes={},
                filename=None,
                search_path=[],
                has_data_files=False,
                namespace_type=None,
                init_module=FrozenModule(
                    name="@@SIX_MOVES@@",
                    loader=loader,
                    distribution=distribution_for_file(spec.origin, path)
                    if spec.origin is not None
                    else None,
                    extension_attributes={},
                    filename=None,
                    globals_written=set(SIX_MOVES_GLOBALS),
                    globals_read=set(),
                ),
            )
            return node, ()

        else:
            # NOTE: Disabling E203 is necessary due to a conflict between flake8 and
            # black. The formatting from black appears to be more correct.

            relative_name = spec.name[spec.name.find(".moves.") + 7 :]  # noqa: E203
            try:
                actual_name = SIX_MOVES_TO[relative_name]
            except KeyError:
                return MissingModule(spec.name), ()

            moved_spec = importlib.util.find_spec(actual_name)
            if moved_spec is None:
                # The moved-to name doesn't actually exist. This
                # can happen on systems where parts of the stdlib
                # are not present, such as some Linux distributions.
                return MissingModule(actual_name), ()

            return node_for_spec(moved_spec, path)

    elif (
        type(loader).__name__ == "VendorImporter"
        and type(loader).__module__ == "setuptools.extern"
    ):
        # Support for ``setuptools.extern.VendorLoader`` in setuptools.
        # This loader loads names names in the ``setuptools.extern`` virtual
        # package from ``setuptools._vendor`` or the system
        # path, whichever is available.
        #
        # That logic is reproduced here.

        root_name: str
        vendor_pkg: str

        assert hasattr(loader, "root_name")
        assert hasattr(loader, "vendor_pkg")

        root_name = loader.root_name  # type: ignore
        vendor_pkg = loader.vendor_pkg  # type: ignore

        relative_name = spec.name[len(root_name) + 1 :]  # noqa: E203

        try:
            moved_spec = importlib.util.find_spec(f"{vendor_pkg}.{relative_name}")
        except ModuleNotFoundError:
            moved_spec = importlib.util.find_spec(relative_name)

        if moved_spec is None:
            return MissingModule(actual_name), ()

        return node_for_spec(moved_spec, path)

    else:
        raise RuntimeError(
            f"Don't known how to handle {loader!r} for {spec.name!r}"
        )  # pragma: nocover

    loader = cast(importlib.abc.InspectLoader, loader)

    if loader.is_package(spec.name):
        node_file = node.filename
        assert node_file is not None

        node_file = node_file.parent

        namespace_type = None
        if (
            source_code is not None
            and "__import__" in node.globals_read
            and any(nm in source_code for nm in ("pkg_resources", "pkgutil"))
        ):
            # This might be an explicit namespace package using
            # setuptools or pkgutil. Import the package to fetch
            # the correct submodule search path.
            try:
                m = importlib.import_module(node.name)
            except ImportError:
                pass
            else:
                spec.submodule_search_locations = getattr(m, "__path__", [])

            if "pkg_resources" in source_code:
                namespace_type = "pkg_resources"
            else:
                assert "pkgutil" in source_code
                namespace_type = "pkgutil"

        assert spec.submodule_search_locations is not None

        package = Package(
            name=node.name,
            loader=node.loader,
            distribution=node.distribution,
            extension_attributes={},
            filename=node_file,
            init_module=node,
            search_path=[
                pathlib.Path(adjust_path(loc))
                for loc in spec.submodule_search_locations
            ],
            has_data_files=_contains_datafiles(node_file),
            namespace_type=namespace_type,
        )

        return package, imports

    return node, imports


def relative_package(importing_module: BaseNode, import_level: int):
    assert import_level > 0

    if isinstance(importing_module, (Package, NamespacePackage)):
        import_level -= 1

    bits = importing_module.name.rsplit(".", import_level)

    if len(bits) < import_level + 1:
        # Invalid relative import
        return None

    return bits[0]
