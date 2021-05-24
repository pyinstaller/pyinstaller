# -*- coding: utf-8 -*-
"""
Tools for searching bytecode for key statements which indicate need for
additional resources e.g. data file, package metadata.

By *bytecode* I mean the ``code`` object given by ``compile()``, accessible
from the ``__code__`` attribute of any non-builtin function or, in
PyInstallerLand, the ``PyiModuleGraph.node("some.module").code`` attribute.
The best guide for bytecode format I've found is the disassembler reference:
https://docs.python.org/3/library/dis.html

This parser implementation aims to combine the flexibility and speed of regex
with the clarity of the output of ``dis.dis(code)``. It hasn't achieved the 2nd
but C'est la vie...

The biggest clarity killer here is the ``EXTENDED_ARG`` opcode which can appear
almost anywhere and therefore needs to be tiptoed around at every step.
If this code needs to expand significantly then I would recommend to upgrade to
a regex-based grammar parsing library such as Reparse. This way, little steps
like unpacking ``EXTENDED_ARGS`` can be defined once then simply referenced
forming a nice hierarchy rather than copied everywhere its needed.

"""

import dis
import re
from types import CodeType


def _instruction_to_regex(x: str):
    """Get a regex-escaped opcode byte from its human readable name."""
    if x not in dis.opname:  # pragma: no cover
        # These opcodes are available only in Python >=3.7.
        # For our purposes, these aliases will do.
        if x == "LOAD_METHOD":
            x = "LOAD_ATTR"
        elif x == "CALL_METHOD":
            x = "CALL_FUNCTION"
    return re.escape(bytes([dis.opmap[x]]))


def bytecode_regex(pattern: bytes, flags=re.VERBOSE | re.DOTALL):
    """A regex powered Python bytecode matcher.

    ``bytecode_regex`` provides a very thin wrapper around :func:`re.compile`.

      * Any opcode names wrapped in backticks are substituted for their
        corresponding opcode bytes.
      * Patterns are compiled in VERBOSE mode by default so that whitespace and
        comments may be used.

    This aims to mirror the output of :func:`dis.dis` which is far more
    readable than looking at raw byte strings.

    """
    assert isinstance(pattern, bytes)

    # Replace anything wrapped in backticks with regex-escaped opcodes.
    pattern = re.sub(
        rb"`(\w+)`",
        lambda m: _instruction_to_regex(m[1].decode()),
        pattern,
    )
    return re.compile(pattern, flags=flags)


# language=PythonVerboseRegExp
_call_function_bytecode = bytecode_regex(rb"""
    # Matches `global_function('some', 'constant', 'arguments')`.

    # Load the global function.
    # In code with >256 of names, this may require extended name references.
    ((?:`EXTENDED_ARG`.)*
     (?:`LOAD_NAME`|`LOAD_GLOBAL`|`LOAD_FAST`).)

    # For foo.bar.whizz(), the above is the 'foo', below is the 'bar.whizz'.
    ((?:(?:`EXTENDED_ARG`.)*
     (?:`LOAD_METHOD`|`LOAD_ATTR`).)*)

    # Load however many arguments it takes. These (for now) must all be
    # constants. Again, code with >256 constants may need extended enumeration.
    ((?:(?:`EXTENDED_ARG`.)*
     `LOAD_CONST`.)*)

    # Call the function. The parameter is the argument count (which may also be
    # >256).
    ((?:`EXTENDED_ARG`.)*
     (?:`CALL_FUNCTION`|`CALL_METHOD`).)

""")

# language=PythonVerboseRegExp
_extended_arg_bytecode = bytecode_regex(rb"""(

    # Arbitrary number of EXTENDED_ARG pairs.
    (?:`EXTENDED_ARG`.)*

    # Followed by some other instruction (usually a LOAD).
    [^`EXTENDED_ARG`].

)""")


def extended_arguments(extended_args: bytes):
    """Unpack the (extended) integer used to reference names or constants.

    The input should be a bytecode snippet of the following form::

        EXTENDED_ARG    ?      # Repeated 0-4 times.
        LOAD_xxx        ?      # Any of LOAD_NAME/LOAD_CONST/LOAD_METHOD/...

    Each ? byte combined together gives the number we want.

    """
    return int.from_bytes(extended_args[1::2], "big")


def load(raw: bytes, code: CodeType) -> str:
    """Parse an (extended) LOAD_xxx instruction."""
    # Get the enumeration.
    index = extended_arguments(raw)

    # Work out what that enumeration was for (constant/local var/global var).

    # If the last instruction byte is a LOAD_FAST:
    if raw[-2] == dis.opmap["LOAD_FAST"]:
        # Then this is a local variable.
        return code.co_varnames[index]
    # Or if it's a LOAD_CONST:
    if raw[-2] == dis.opmap["LOAD_CONST"]:
        # Then this is a literal.
        return code.co_consts[index]
    # Otherwise, it's a global name.
    return code.co_names[index]


def loads(raw: bytes, code: CodeType) -> list:
    """Parse multiple consecutive LOAD_xxx instructions. Or load() in a for
    loop.

    May be used to unpack a function's parameters or nested attributes
    ``(foo.bar.pop.whack)``.

    """
    return [load(i, code) for i in _extended_arg_bytecode.findall(raw)]


def function_calls(code: CodeType) -> list:
    """Scan a code object for all function calls on constant arguments."""
    match: re.Match
    out = []

    for match in _call_function_bytecode.finditer(code.co_code):
        function_root, methods, args, arg_count = match.groups()

        # For foo():
        #   `function_root` contains 'foo' and `methods` is empty.
        # For foo.bar.whizz():
        #   `function_root` contains 'foo' and `methods` contains the rest.
        function_root = load(function_root, code)
        methods = loads(methods, code)
        function = ".".join([function_root] + methods)

        args = loads(args, code)
        arg_count = extended_arguments(arg_count)

        if arg_count != len(args):
            # This happens if there are variable or keyword arguments.
            # Bail out in either case.
            continue

        out.append((function, args))

    return out


def search_recursively(search: callable, code: CodeType, _memo=None) -> dict:
    """Apply a search function to a code object, recursing into child code
    objects (function definitions)."""
    if _memo is None:
        _memo = {}
    if code not in _memo:
        _memo[code] = search(code)
        for const in code.co_consts:
            if isinstance(const, CodeType):
                search_recursively(search, const, _memo)
    return _memo


def recursive_function_calls(code: CodeType) -> dict:
    """Scan a code object, recursing into function definitions and bodies of
    comprehension loops, for function calls on constant arguments."""
    return search_recursively(function_calls, code)


def any_alias(full_name: str):
    """List possible aliases of a fully qualified Python name.

        >>> list(any_alias("foo.bar.wizz"))
        ['foo.bar.wizz', 'bar.wizz', 'wizz']

    This crudely allows us to capture uses of wizz() under any of
    ::
        import foo
        foo.bar.wizz()
    ::
        from foo import bar
        bar.wizz()
    ::
        from foo.bar import wizz
        wizz()

    However, it'll fail for any form of aliases and quite likely find false
    matches.

    """
    parts = full_name.split('.')
    while parts:
        yield ".".join(parts)
        parts = parts[1:]
