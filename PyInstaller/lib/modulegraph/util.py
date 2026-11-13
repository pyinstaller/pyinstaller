from __future__ import annotations

import dis
import inspect
import logging
import sys
from types import CodeType
from typing import Any, Callable, Iterator, Protocol, cast

from PyInstaller import compat

logger = logging.getLogger(__name__)

_selected_implementation: Callable[[CodeType], Iterator[ModuleGraphInstruction]] | None = None


class ModuleGraphInstruction(Protocol):
    """What modulegraph reads from an instruction."""
    @property
    def opname(self) -> str:
        ...

    @property
    def argval(self) -> Any:
        ...


def iterate_instructions(code_object):
    """Delivers the byte-code instructions as a continuous stream.

    Yields `ModuleGraphInstruction`. After each code-block (`co_code`), `None` is
    yielded to mark the end of the block and to interrupt the steam.
    """
    global _selected_implementation
    if _selected_implementation is None:
        _selected_implementation = _select_implementation() if compat.fast_bytecode_scan else _get_instructions_safe
    return _iterate_recursively(code_object, _selected_implementation)


def _get_instructions_safe(code_object: CodeType) -> Iterator[dis.Instruction]:
    """Default, non-optimized implementation."""
    # The arg extension the EXTENDED_ARG opcode represents is automatically handled by get_instructions() but the
    # instruction is left in. Get rid of it to make subsequent parsing easier/safer.
    return (i for i in dis.get_instructions(code_object) if i.opname != "EXTENDED_ARG")


def _iterate_recursively(
    code_object: CodeType,
    get_instructions: Callable[[CodeType], Iterator[ModuleGraphInstruction]],
) -> Iterator[ModuleGraphInstruction | None]:
    """Yield instructions for the given code object, then `None`, then the same for each code object nested in it."""
    yield from get_instructions(code_object)

    yield None

    # For each constant in this code object that is itself a code object,
    # parse this constant in the same manner.
    for constant in code_object.co_consts:
        if inspect.iscode(constant):
            yield from _iterate_recursively(constant, get_instructions)


def _get_instructions_fast(code_object: CodeType) -> Iterator[SlimInstruction]:
    code = _Code(code_object)
    opname = dis.opname  # Slightly faster than inlining the lookup.
    EXTENDED_ARG = dis.EXTENDED_ARG  # Slightly faster than inlining the lookup.
    # `_unpack_opargs` is what `dis.get_instructions` uses to walk the bytecode:
    #     https://github.com/python/cpython/blob/v3.14.7/Lib/dis.py#L675
    #     https://github.com/python/cpython/blob/v3.14.7/Lib/dis.py#L771
    # It yields `(offset, op, arg)` on Python <= 3.12 and `(offset, start_offset, op, arg)` on Python >= 3.13:
    #     https://github.com/python/cpython/blob/v3.12.16/Lib/dis.py#L645
    #     https://github.com/python/cpython/blob/v3.13.0/Lib/dis.py#L887-L890
    _unpack_opargs = cast(
        # Type expressed as a string for Python 3.8 and 3.9 compatibility:
        "Callable[[bytes], Iterator[tuple[int, int, int | None]] | Iterator[tuple[int, int, int, int | None]]]",
        dis._unpack_opargs,
    )
    for offset, *_, op, arg in _unpack_opargs(code_object.co_code):
        if op == EXTENDED_ARG:
            continue  # Like the original, skip these. Their effect is already included in `arg`.
        yield SlimInstruction(opname[op], code, op, arg, offset)


def _select_implementation() -> Callable[[CodeType], Iterator[ModuleGraphInstruction]]:
    try:
        difference = _diff_between_implementations()
    except Exception:
        # Any exception means that some assumption about CPython's internals no longer holds.
        logger.warning(_FALLBACK_WARNING, "the self-test raised an exception", exc_info=True)
        return _get_instructions_safe

    if difference is not None:
        logger.warning(_FALLBACK_WARNING, difference)
        return _get_instructions_safe

    return _get_instructions_fast


# `dis.ArgResolver` computes `argval` for `dis.get_instructions` on Python >= 3.13:
#     https://github.com/python/cpython/blob/v3.13.0/Lib/dis.py#L625-L628
_HAS_ARG_RESOLVER = hasattr(dis, "ArgResolver")
if _HAS_ARG_RESOLVER:
    # The jump label map is only needed for the `argval` of jumps, and is expensive to compute.
    _NEEDS_LABELS_MAP = frozenset(dis.hasjump) | frozenset(dis.hasexc)
else:
    # Python <= 3.12 no longer changes, so the `argval` of frequently read opcodes can safely be computed directly:
    #     https://github.com/python/cpython/blob/v3.12.0/Lib/dis.py#L470-L487
    # The self-test checks this too.
    _NAME_OPS = frozenset(
        dis.opmap[name] for name in ("IMPORT_NAME", "STORE_NAME", "STORE_GLOBAL", "DELETE_NAME", "DELETE_GLOBAL")
    )
    _CONST_OPS = frozenset({dis.opmap["LOAD_CONST"]})


class _Code:
    """Per-code-object state shared by its instructions, for computing `argval` on demand."""

    __slots__ = ("_arg_resolver", "_arg_resolver_with_labels", "_argvals", "code")

    def __init__(self, code):
        self.code = code
        self._arg_resolver = None
        self._arg_resolver_with_labels = None
        self._argvals = None

    def argval(self, op, arg, offset):
        co = self.code
        if _HAS_ARG_RESOLVER:
            if op in _NEEDS_LABELS_MAP:
                if self._arg_resolver_with_labels is None:
                    self._arg_resolver_with_labels = self._make_arg_resolver(dis._make_labels_map(co.co_code))
                return self._arg_resolver_with_labels.get_argval_argrepr(op, arg, offset)[0]
            if self._arg_resolver is None:
                self._arg_resolver = self._make_arg_resolver(None)
            return self._arg_resolver.get_argval_argrepr(op, arg, offset)[0]
        if op in _NAME_OPS:
            return co.co_names[arg]
        if op in _CONST_OPS:
            return co.co_consts[arg]
        if self._argvals is None:
            self._argvals = {i.offset: i.argval for i in dis.get_instructions(co)}
        return self._argvals[offset]

    def _make_arg_resolver(self, labels_map):
        # The same way `dis.get_instructions` does it.
        co = self.code
        return dis.ArgResolver(
            co_consts=co.co_consts,
            names=co.co_names,
            varname_from_oparg=co._varname_from_oparg,
            labels_map=labels_map,
        )


class SlimInstruction:
    """A slimmed-down version of `dis.Instruction`, with `argval` computed on demand."""

    __slots__ = ("_arg", "_code", "_offset", "_op", "opname")

    def __init__(self, opname: str, code: _Code, op: int, arg: int | None, offset: int):
        self.opname = opname
        self._code = code
        self._op = op
        self._arg = arg
        self._offset = offset

    @property
    def argval(self):
        return self._code.argval(self._op, self._arg, self._offset)


# Main code for the self-test. It should exercise as many kinds of instructions as possible.
_SELF_TEST_CODE_MAIN = """
import os, os.path as p, xml.etree.ElementTree
from . import a
from .. import b as c
from collections import *
from collections.abc import (Mapping, Sequence)
x = None; y = True; z = False; e = ''; m = -1; n = 255; o = 256; q = 2 ** 100; f = 1.5; t = (1, 'a'); s = frozenset({1})
b = b'x'; cplx = 1j; ell = ...
del x
global gg
gg = 1
def func(arg, *args, kw=0, **kwargs):
    global G
    import json
    from json import dumps
    G = 1
    del G
    try:
        import missing
    except ImportError:
        pass
    for i in range(3):
        if i: break
    while arg: arg -= 1
    with open(arg) as fh: pass
    l = [v for v in args if v]
    g = (v for v in args)
    def inner(): nonlocal l; return l
    return f"{arg!r:>{kw}}" + str(lambda: 0)
class K:
    import sys
    attr = 1
    def method(self): return super().method()
async def coro():
    async with ctx() as v: await v
    async for v in it(): yield v
""" + "\n".join(f"name{i} = {i}.5" for i in range(300))  # More than 256 names and constants, for EXTENDED_ARG.

_SELF_TEST_CODE_MATCH = """
match x:
    case [1, *rest]: pass
    case {"k": v}: pass
    case K(attr=1): pass
    case _: pass
"""

_SELF_TEST_CODE_LAZY_IMPORTS = "lazy import lazily_imported\nlazy from a import b\n"

_SELF_TEST_CODE_SNIPPETS_WITH_MIN_VERSIONS = [
    ((3, 8), _SELF_TEST_CODE_MAIN),
    ((3, 10), _SELF_TEST_CODE_MATCH),
    ((3, 15), _SELF_TEST_CODE_LAZY_IMPORTS),
]

_FALLBACK_WARNING = (
    "Fast bytecode scanning does not work as expected on this Python version (%s); "
    "falling back to the slower implementation. Please report this."
)


def _diff_between_implementations():
    codes: list[CodeType] = []
    for (min_version, snippet) in _SELF_TEST_CODE_SNIPPETS_WITH_MIN_VERSIONS:
        if (sys.version_info >= min_version):
            codes.append(compile(snippet, "<self_test_code>", "exec", dont_inherit=True))

    for code in codes:
        expected = [
            None if i is None else (i.opname, i.argval) for i in _iterate_recursively(code, _get_instructions_safe)
        ]
        actual = [
            None if i is None else (i.opname, i.argval) for i in _iterate_recursively(code, _get_instructions_fast)
        ]
        if actual != expected:
            k = next((k for k, (a, b) in enumerate(zip(actual, expected)) if a != b), min(len(actual), len(expected)))
            return f"instruction {k} is {actual[k:k + 1]} instead of {expected[k:k + 1]}"
    return None
