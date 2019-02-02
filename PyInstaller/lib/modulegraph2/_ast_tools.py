"""
Tools for working with the AST for a module. This currently just defines
a function for extracting information about import statements from the AST.
"""
import ast
import collections
from typing import Deque, Iterator, Tuple

from ._importinfo import ImportInfo, create_importinfo


def extract_ast_info(node: ast.AST) -> Iterator[ImportInfo]:
    """
    Scan the AST for a module to look for import statements.

    The AST scanner gives the most detailed information about import statements,
    and includes information about renames (``import ... as ...``), and the
    location of imports (global, in a function, in a try/except statement, in a
    conditional statement).

    The scanner explicitly manages a work queue and will not recurse to avoid
    exhausting the stack.

    Args:
      node: The AST for a module

    Returns:
      An iterator that yields information about all located import statements
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
                yield create_importinfo(
                    (nm.name, nm.asname), None, 0, in_def, in_if, in_tryexcept
                )

        elif isinstance(node, ast.ImportFrom):
            yield create_importinfo(
                (node.module or "", None),
                {(nm.name, nm.asname) for nm in node.names},
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
