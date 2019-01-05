"""
Tooling to create the AST for a module
and extract information from it.
"""
import ast
import collections
import dataclasses
from typing import Iterator, Set, Tuple, Deque


# import os
# import importlib.util
# XXX: Not sure if this will be needed...
# def ast_for_file(path: os.PathLike, module_source: Optional[str] = None) -> ast.AST:
#    """
#    Return the AST for the given module or script
#    """
#    if module_source is None:
#        with open(path, "rb") as fp:
#            module_bytes = fp.read()
#
#        module_source = importlib.util.decode_source(module_bytes)
#
#    ast = compile(
#        module_source, os.fspath(path), "exec", flags=ast.PyCF_ONLY_AST,
#        dont_inherit=True
#    )
#    return ast


@dataclasses.dataclass(frozen=True)
class ImportInfo:
    """
    Information about an import statement found in the AST for a module or script
    """

    import_module: str
    import_level: int
    import_names: Set[str]
    star_import: bool
    is_in_function: bool
    is_in_conditional: bool
    is_in_tryexcept: bool

    @property
    def is_optional(self):
        return self.is_in_function or self.is_in_conditional or self.is_in_tryexcept


def _create_importinfo(name, fromlist, level, in_def, in_if, in_tryexcept):

    have_star = False
    if fromlist is None:
        import_names = set()
    else:
        import_names = set(fromlist)
        if "*" in import_names:
            import_names.remove("*")
            have_star = True

    return ImportInfo(
        import_module=name,
        import_level=level,
        import_names=import_names,
        star_import=have_star,
        is_in_function=in_def,
        is_in_conditional=in_if,
        is_in_tryexcept=in_tryexcept,
    )


def extract_ast_info(node: ast.AST) -> Iterator[ImportInfo]:
    """
    Look for import statements in the AST and return information about them
    """
    # The obvious way to walk the AST is to use a NodeVisitor, but
    # that can exhaust the stack. Therefore this function iteratively
    # works the ast keeping state on a manual work queue.
    work_q: Deque[Tuple[ast.AST, bool, bool, bool]] = collections.deque()
    work_q.append((node, False, False, False))
    while work_q:
        node, in_def, in_if, in_tryexcept = work_q.popleft()

        if isinstance(node, ast.Import):
            for nm in node.names:
                yield _create_importinfo(nm.name, None, 0, in_def, in_if, in_tryexcept)

        elif isinstance(node, ast.ImportFrom):
            yield _create_importinfo(
                node.module or "",
                {nm.name for nm in node.names},
                node.level,
                in_def,
                in_if,
                in_tryexcept,
            )

        elif isinstance(node, ast.If):
            for child in ast.iter_child_nodes(node):
                work_q.append((child, in_def, True, in_tryexcept))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.iter_child_nodes(node):
                work_q.append((child, True, in_if, in_tryexcept))

        elif isinstance(node, (ast.Try)):
            for name, children in ast.iter_fields(node):
                if name == "finalbody":
                    for child in children:
                        work_q.append((child, in_def, in_if, in_tryexcept))
                else:
                    for child in children:
                        work_q.append((child, in_def, in_if, True))

        else:
            for child in ast.iter_child_nodes(node):
                work_q.append((child, in_def, in_if, in_tryexcept))
