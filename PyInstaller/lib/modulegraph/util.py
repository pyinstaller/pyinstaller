from __future__ import annotations

import dis
import inspect
import logging

logger = logging.getLogger(__name__)


def iterate_instructions(code_object):
    """Delivers the byte-code instructions as a continuous stream.

    Yields `SlimInstruction`. After each code-block (`co_code`), `None` is
    yielded to mark the end of the block and to interrupt the steam.
    """
    # The arg extension the EXTENDED_ARG opcode represents is automatically handled by get_instructions() but the
    # instruction is left in. Get rid of it to make subsequent parsing easier/safer.
    yield from (i for i in _get_instructions_fast(code_object) if i.opname != "EXTENDED_ARG")

    yield None

    # For each constant in this code object that is itself a code object,
    # parse this constant in the same manner.
    for constant in code_object.co_consts:
        if inspect.iscode(constant):
            yield from iterate_instructions(constant)


def _get_instructions_fast(code_object):
    code = _Code(code_object)
    opname = dis.opname  # Slightly faster than inlining the lookup.
    # `_unpack_opargs` is what `dis.get_instructions` uses to walk the bytecode:
    #     https://github.com/python/cpython/blob/v3.14.7/Lib/dis.py#L675
    #     https://github.com/python/cpython/blob/v3.14.7/Lib/dis.py#L771
    # It yields `(offset, op, arg)` on Python <= 3.12 and `(offset, start_offset, op, arg)` on Python >= 3.13:
    #     https://github.com/python/cpython/blob/v3.12.16/Lib/dis.py#L645
    #     https://github.com/python/cpython/blob/v3.13.0/Lib/dis.py#L887-L890
    for offset, *_, op, arg in dis._unpack_opargs(code_object.co_code):
        yield SlimInstruction(opname[op], code, op, arg, offset)


# `dis.ArgResolver` computes `argval` for `dis.get_instructions` on Python >= 3.13:
#     https://github.com/python/cpython/blob/v3.13.0/Lib/dis.py#L625-L628
_HAS_ARG_RESOLVER = hasattr(dis, "ArgResolver")
if _HAS_ARG_RESOLVER:
    # The jump label map is only needed for the `argval` of jumps, and is expensive to compute.
    _NEEDS_LABELS_MAP = frozenset(dis.hasjump) | frozenset(dis.hasexc)
else:
    # Python <= 3.12 no longer changes, so the `argval` of frequently read opcodes can safely be computed directly:
    #     https://github.com/python/cpython/blob/v3.12.0/Lib/dis.py#L470-L487
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

    def _make_arg_resolver(self, maybe_labels_map):
        # The same way `dis.get_instructions` does it.
        #     https://github.com/python/cpython/blob/v3.14.7/Lib/dis.py#L671-L674
        co = self.code
        return dis.ArgResolver(
            co_consts=co.co_consts,
            names=co.co_names,
            varname_from_oparg=co._varname_from_oparg,
            labels_map=maybe_labels_map,
        )


class SlimInstruction:
    """A slimmed-down version of `dis.Instruction`, with `argval` computed on demand."""

    __slots__ = ("_arg", "_code", "_offset", "_op", "opname")

    def __init__(self, opname, code, op, arg, offset):
        self.opname = opname
        self._code = code
        self._op = op
        self._arg = arg
        self._offset = offset

    @property
    def argval(self):
        return self._code.argval(self._op, self._arg, self._offset)
