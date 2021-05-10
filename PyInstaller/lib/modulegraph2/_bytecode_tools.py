"""
Tools for working with the bytecode for a module. This currently just
defines a function for extracting information about import statements
and the use of global names.
"""
import collections
import dis
import types
from typing import Deque, Dict, Iterator, List, Optional, Set, Tuple

from ._importinfo import ImportInfo, create_importinfo


def _all_code_objects(
    code: types.CodeType,
) -> Iterator[Tuple[types.CodeType, List[types.CodeType]]]:
    """
    Yield all code objects directly and indirectly referenced from
    *code* (including *code* itself).

    This could explicitly manages a work queue and does not recurse
    to avoid exhausting the stack.

    Args:
      code: A code object

    Returns:
      An iterator that yields tuples *(child_code, parents)*, where *parents*
      is a list all code objects in the reference chain from *code*.
    """
    work_q: Deque[types.CodeType] = collections.deque()
    work_q.append(code)

    parents: Dict[types.CodeType, List[types.CodeType]] = {}

    while work_q:
        current = work_q.popleft()
        yield current, parents.get(current, [])
        for value in current.co_consts:
            if isinstance(value, types.CodeType):
                work_q.append(value)
                parents[value] = parents.get(current, []) + [value]


def _extract_single(code: types.CodeType, is_function_code: bool, is_class_code: bool):
    """
    Extract import information from a single bytecode object (without recursing
    into child objects).

    Args:
      code: The code object to process

      is_function_code: True if this is a code object for a function or
        anything in a function.

      is_class_code: True if this is the code object for a class
    """
    instructions = list(dis.get_instructions(code))

    imports: List[ImportInfo] = []
    globals_written: Set[str] = set()
    globals_read: Set[str] = set()
    func_codes: Set[types.CodeType] = set()
    class_codes: Set[types.CodeType] = set()
    fromvalues: Optional[List[Tuple[str, Optional[str]]]]

    for offset, inst in enumerate(instructions):
        if inst.opname == "IMPORT_NAME":
            from_inst_offset = 1
            if instructions[offset - from_inst_offset].opname == "EXTENDED_ARG":
                from_inst_offset += 1

            level_inst_offset = from_inst_offset + 1
            if instructions[offset - level_inst_offset].opname == "EXTENDED_ARG":
                level_inst_offset += 1

            assert (
                instructions[offset - from_inst_offset].opname == "LOAD_CONST"
            ), instructions[offset - 1].opname
            assert instructions[offset - level_inst_offset].opname == "LOAD_CONST", (
                instructions[offset - 2].opname,
                code,
            )

            from_offset = instructions[offset - from_inst_offset].arg
            assert from_offset is not None

            level_offset = instructions[offset - level_inst_offset].arg
            assert level_offset is not None

            fromlist = code.co_consts[from_offset]
            level = code.co_consts[level_offset]

            assert fromlist is None or isinstance(fromlist, tuple)

            name_offset = inst.arg
            assert name_offset is not None

            import_module = code.co_names[name_offset]

            if fromlist is not None:
                fromvalues = [(nm, None) for nm in fromlist]
            else:
                fromvalues = None

            imports.append(
                create_importinfo(
                    (import_module, None),
                    fromvalues,
                    level,
                    is_function_code,
                    False,
                    False,
                )
            )
            if not (is_function_code or is_class_code):
                if fromlist is not None:
                    globals_written |= set(fromlist) - {"*"}

        elif inst.opname in ("STORE_NAME", "STORE_NAME"):
            if is_class_code and inst.opname == "STORE_NAME":
                continue

            const_offset = inst.arg
            assert const_offset is not None
            globals_written.add(code.co_names[const_offset])

        elif inst.opname in ("LOAD_GLOBAL", "LOAD_NAME"):
            if is_class_code and inst.opname == "LOAD_NAME":
                continue

            const_offset = inst.arg
            assert const_offset is not None
            globals_read.add(code.co_names[const_offset])

        elif inst.opname == "MAKE_FUNCTION":
            const_offset = instructions[offset - 2].arg
            assert const_offset is not None

            if offset >= 3 and instructions[offset - 3].opname == "LOAD_BUILD_CLASS":
                class_codes.add(code.co_consts[const_offset])
            else:
                func_codes.add(code.co_consts[const_offset])

    return imports, globals_written, globals_read, func_codes, class_codes


def _is_code_for_function(
    code: types.CodeType, parents: List[types.CodeType], func_codes: Set[types.CodeType]
):
    """
    Check if this is the code object for a function or inside a function

    Args:
      code: The code object to check

      parents: List of parents for this code object

      func_codes: Set of code objects that are directly for functions
    """
    return code in func_codes or any(p in func_codes for p in parents)


def extract_bytecode_info(
    code: types.CodeType,
) -> Tuple[List[ImportInfo], Set[str], Set[str]]:
    """
    Extract interesting information from the code object for a module or script

    Returns a tuple of three items:
    1) List of all imports
    2) A set of global names written
    3) A set of global names read by
    """
    # Note: This code is iterative to avoid exhausting the stack in
    # patalogical code bases (in particular deeply nested functions)
    all_imports: List[ImportInfo] = []
    all_globals_written: Set[str] = set()
    all_globals_read: Set[str] = set()
    all_func_codes: Set[types.CodeType] = set()
    all_class_codes: Set[types.CodeType] = set()

    for current, parents in _all_code_objects(code):
        (
            imports,
            globals_written,
            globals_read,
            func_codes,
            class_codes,
        ) = _extract_single(
            current,
            _is_code_for_function(current, parents, all_func_codes),
            current in all_class_codes,
        )
        all_imports += imports
        all_globals_written |= globals_written
        all_globals_read |= globals_read
        all_func_codes |= func_codes
        all_class_codes |= class_codes

    return all_imports, all_globals_written, all_globals_read
