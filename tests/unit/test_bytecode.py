#-----------------------------------------------------------------------------
# Copyright (c) 2021-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
"""
Tests for PyInstaller.depend.bytecode
"""

import re
from types import CodeType
from textwrap import dedent, indent
import operator

from PyInstaller import compat
from PyInstaller.depend.bytecode import (
    function_calls,
    recursive_function_calls,
    any_alias,
    finditer,
    _cleanup_bytecode_string,  # used for sanity check in test_finditer()
)


def compile_(x):
    return compile(dedent(x), "<no file>", "exec")


def many_int_constants():
    """
    Generate Python code that includes >256 integer constants.
    """
    # NOTE: in python >= 3.14.0a2, integer arguments smaller than 256 are pushed directly to stack, without using a
    # co_consts. Therefore, to effectively use >256 constants, we need to generate >512 integer arguments.
    return "".join(f'a = {i}\n' for i in range(600))


def many_str_constants():
    """
    Generate Python code that includes >256 string constants.
    """
    return "".join(f'a = "val_{i}"\n' for i in range(300))


def many_globals():
    """
    Generate Python code that includes >256 of global identifiers.
    """
    return " = ".join(f"a_{i}" for i in range(300)) + " = 'hello'\n"


def many_arguments():
    """
    Generate a function call taking >256 arguments.
    """
    return 'foo({})\n'.format(", ".join(map(str, range(300))))


def in_a_function(body):
    """
    Define a function called function() containing **body**.
    """
    return "def function():\n" + indent(body, "    ") + "\n"


# Sanity check that no fancy bytecode optimisation causes code from either of the above functions to be automatically
# removed as redundant by the compiler.


def test_many_int_constants():
    code: CodeType = compile_(many_int_constants())
    # Only the variable name 'a'.
    assert code.co_names == ('a',)

    # In python >= 3.14.0a2, LOAD_SMALL_INT instruction is used to push integers smaller than 256 on the stack, and
    # co_consts is used for larger values (in combination with LOAD_CONST / LOAD_CONST_IMMORTAL).
    # In earlier python versions, co_consts is used for all constants.
    if compat.is_py314:
        # In 3.14.0a7 the behavior was changed (by 55815a6); it seems that the value of very first LOAD_SMALL_INT is
        # added to co_consts for some reason. This does not happen if there is preceding LOAD_CONST (e.g., if there
        # is a docstring present before the code). In case this behavior change was unintended or is changed further,
        # check if co_consts contains 0 at first index and adjust expected length accordingly...
        expected_length = 601 - 256  # (600 - 256) integers plus a `None` return.
        if code.co_consts[0] == 0:
            expected_length += 1
        assert len(code.co_consts) == expected_length
    else:
        # 600 integers plus a 'None' return.
        assert len(code.co_consts) == 601


def test_many_str_constants():
    code: CodeType = compile_(many_str_constants())
    # Only the variable name 'a'.
    assert code.co_names == ('a',)

    # 300 string constants plus a 'None' return.
    assert len(code.co_consts) == 301


def test_many_globals():
    code: CodeType = compile_(many_globals())
    assert len(code.co_names) == 300
    assert len(code.co_consts) == 2


def test_global_functions():
    """
    Test finding function calls in the global namespace.
    """

    # The simplest possible function call.
    code = compile_("foo()")
    assert function_calls(code) == [('foo', [])]

    # With arguments.
    code = compile_("foo('a')")
    assert function_calls(code) == [('foo', ['a'])]

    # Having >256 constants will take us into extended arg territory where multiple byte-pair instructions are needed
    # to reference the constant. If everything works, we should not notice the difference.
    code = compile_(many_int_constants() + "foo(.123)")
    assert function_calls(code) == [('foo', [.123])]

    code = compile_(many_str_constants() + "foo(.321)")
    assert function_calls(code) == [('foo', [.321])]

    # Similarly, >256 global names also requires special handling.
    code = compile_(many_globals() + "foo(.456)")
    assert function_calls(code) == [('foo', [.456])]

    # And the unlikely case of >256 arguments to one function call.
    #
    # NOTE: with python >= 3.14.0a5, this creates a list with a sequence
    # of BUILD_LIST, LOAD*, LIST_APPEND opcodes, followed by a
    # CALL_INTRINSIC_1 opcode with INTRINSIC_LIST_TO_TUPLE argument,
    # and CALL_FUNCTION_EX opcode.
    #
    # Since we have no real use case for such lists, perform the
    # test only on earlier python versions.
    if not compat.is_py314:
        code = compile_(many_arguments())
        assert function_calls(code) == [('foo', list(range(300)))]

    # For loops, if statements should work. The iterable in a comprehension loop works but the statement to be executed
    # repeatedly gets its own code object and therefore requires recursion (tested later).
    code = compile_(
        """
        for i in foo(1, 2):
            a = bar(3)
            if wop(4) > whip(5):
                whiz(6)
                [7 for i in whallop(8)]
        """
    )
    assert function_calls(code) == [
        ("foo", [1, 2]),
        ("bar", [3]),
        ("wop", [4]),
        ("whip", [5]),
        ("whiz", [6]),
        ("whallop", [8]),
    ]

    # These are not supported but should be silently ignored without unintentional errors:
    assert function_calls(compile_("foo(x)")) == []
    assert function_calls(compile_("foo(a='3')")) == []
    assert function_calls(compile_("foo(bar())")) == [('bar', [])]

    # Python's compiler evaluates arithmetic.
    out = function_calls(compile_("foo(1 + 1)"))
    if out:
        # However, I will not bank on this being guaranteed behaviour.
        assert out == [("foo", [2])]

    assert function_calls(compile_("foo.bar()")) == [("foo.bar", [])]
    assert function_calls(compile_("foo.bar.pop.whack('a', 'b')")) == [("foo.bar.pop.whack", ['a', 'b'])]


def test_nested_codes():
    """
    Test function_calls() on global functions in nested code objects (bodies of other functions).
    """

    # The following compile() creates 3 code objects:
    #   - A global code.
    #   = The contents of foo().
    #   - And the body of the embedded lambda.

    code = compile_(
        """
        def foo():
            bar()
            whoop = lambda : fizz(3)
            return range(10)
        """
    )
    # There are no function calls in the global code.
    assert function_calls(code) == []

    # Get the body of foo().
    foo_code, = (i for i in code.co_consts if isinstance(i, CodeType))
    # foo() contains bar() and the iterable of the comprehension loop.
    assert function_calls(foo_code) == [('bar', []), ('range', [10])]

    # Get the body of the embedded lambda.
    lambda_code = next(i for i in foo_code.co_consts if isinstance(i, CodeType))
    # This contains fizz(3).
    assert function_calls(lambda_code) == [('fizz', [3])]

    assert recursive_function_calls(code) == {
        code: [],
        foo_code: [('bar', []), ('range', [10])],
        lambda_code: [('fizz', [3])],
    }


def test_local_functions():
    """
    Test on purely local functions. I.e., the function was imported and called inside the body of another function.
    """
    code_ = compile_(
        in_a_function(
            """
            a = 3
            import foo, zap
            zap.pop(), foo.bar()
            """
        )
    )

    code: CodeType
    code, = (i for i in code_.co_consts if isinstance(i, CodeType))

    # This test may mistakenly pass if co_names and co_varnames can be mixed up.
    # Ensure co_names[i] != co_varnames[i] holds for all `i`.
    assert all(map(operator.ne, code.co_names, code.co_varnames))

    assert function_calls(code) == [('zap.pop', []), ('foo.bar', [])]


def test_any_alias():
    assert tuple(any_alias("foo.bar.pop")) == ("foo.bar.pop", "bar.pop", "pop")


def test_finditer():
    """
    Test that bytecode.finditer() yields matches only that start on an even byte (``match.start() % 2 == 0``).

    There are 3 permutations here when considering a match:
    - A match starts on an even byte:
        That's good! Include that sequence.
    - A single character match starts on an odd byte:
        Ignore it. It's a false positive.
    - A multi-character match starts on an odd byte:
        This match will be a false positive but there may be a genuine match shortly afterwards (in the case of the
        # test below - it'll be the next character) which overlaps with this one so we must override regex's
        behaviour of ignoring overlapping matches to prevent these from getting lost.
    """

    # separator: 0xFF
    sample_string = b"0123\xFF4567\xFF890\xFF12\xFF3\xFF4"

    # Sanity check - ensure that none of the characters in the sample string coincide with the opcodes that `finditer()`
    # filters out via call to `_cleanup_bytecode_string()` (e.g., CACHE, PUSH_NULL), If that is the case, we need to
    # pick up new separator to avoid disturbing the test. For example, original separator was space character, but its
    # ordinal code (32) coincides with PUSH_NULL opcode in python 3.14.0a7.
    assert sample_string == _cleanup_bytecode_string(sample_string), \
        "One of characters in input string coincides with filtered-out opcode!"

    matches = list(finditer(re.compile(rb"\d+"), sample_string))
    aligned = [i.group() for i in matches]
    assert aligned == [b"0123", b"567", b"890", b"12"]
