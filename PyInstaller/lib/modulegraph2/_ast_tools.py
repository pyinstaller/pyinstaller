"""
Tooling to create the AST for a module
and extract information from it.
"""
import ast
import collections
from typing import Deque, Iterator, Tuple

from ._importinfo import ImportInfo, create_importinfo


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
                # XXX: nm.asname contains the renamed module for "import name as alias"
                yield create_importinfo(nm.name, None, 0, in_def, in_if, in_tryexcept)

        elif isinstance(node, ast.ImportFrom):
            yield create_importinfo(
                node.module or "",
                # XXX: nm.asname contains the renamed module for "import name as alias"
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
