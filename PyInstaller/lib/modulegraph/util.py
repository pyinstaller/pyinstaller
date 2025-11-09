import dis
import inspect
from types import CodeType
from typing import Iterable


def _iter_instructions_no_extarg(code_object: CodeType) -> Iterable[dis.Instruction]:
    """
    Yield instructions for *code_object* filtering out EXTENDED_ARG.
    PyPy's dis.get_instructions() can raise IndexError for certain bytecode
    patterns (see https://foss.heptapod.net/pypy/pypy/-/issues/4391). Fall
    back to dis.Bytecode in that case so we can continue constructing the
    module graph instead of aborting the build.
    """
    for factory in (dis.get_instructions, dis.Bytecode):
        try:
            instructions = list(factory(code_object))
        except (IndexError, ValueError):
            # PyPy 3.11's dis may choke on certain bytecode constructs; try the next fallback.
            continue
        else:
            for instruction in instructions:
                if instruction.opname != "EXTENDED_ARG":
                    yield instruction
            break


def iterate_instructions(code_object):
    """Delivers the byte-code instructions as a continuous stream.

    Yields `dis.Instruction`. After each code-block (`co_code`), `None` is
    yielded to mark the end of the block and to interrupt the steam.
    """
    # The arg extension the EXTENDED_ARG opcode represents is automatically handled by get_instructions() but the
    # instruction is left in. Get rid of it to make subsequent parsing easier/safer.
    yield from _iter_instructions_no_extarg(code_object)

    yield None

    # For each constant in this code object that is itself a code object,
    # parse this constant in the same manner.
    for constant in code_object.co_consts:
        if inspect.iscode(constant):
            yield from iterate_instructions(constant)
