# -*- coding: utf-8 -*-
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
)


def compile_(x):
    return compile(dedent(x), "<no file>", "exec")


def many_constants():
    """
    Generate Python code that includes >256 constants.
    """
    return "".join(f'a = {i}\n' for i in range(300))


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


def test_many_constants():
    code: CodeType = compile_(many_constants())
    # Only the variable name 'a'.
    assert code.co_names == ('a',)

    # 1000 integers plus a 'None' return.
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
    code = compile_(many_constants() + "foo(.123)")
    assert function_calls(code) == [('foo', [.123])]

    # Similarly, >256 global names also requires special handling.
    code = compile_(many_globals() + "foo(.456)")
    assert function_calls(code) == [('foo', [.456])]

    # And the unlikely case of >256 arguments to one function call. This is a syntax error on Python <= 3.6
    if compat.is_py37:
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
    #   - And the body of the comprehension loop.

    code = compile_(
        """
        def foo():
            bar()
            return [fizz(3) for i in range(10)]
        """
    )
    # There are no function calls in the global code.
    assert function_calls(code) == []

    # Get the body of foo().
    foo_code, = (i for i in code.co_consts if isinstance(i, CodeType))
    # foo() contains bar() and the iterable of the comprehension loop.
    assert function_calls(foo_code) == [('bar', []), ('range', [10])]

    # Get the body of the comprehension loop.
    list_code, = (i for i in foo_code.co_consts if isinstance(i, CodeType))
    # This contains fizz(3).
    assert function_calls(list_code) == [('fizz', [3])]

    assert recursive_function_calls(code) == {
        code: [],
        foo_code: [('bar', []), ('range', [10])],
        list_code: [('fizz', [3])],
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
    matches = list(finditer(re.compile(r"\d+"), "0123 4567 890 12 3 4"))
    aligned = [i.group() for i in matches]
    assert aligned == ["0123", "567", "890", "12"]
