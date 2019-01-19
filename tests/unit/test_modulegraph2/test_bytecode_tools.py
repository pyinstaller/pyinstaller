import ast
import unittest

from modulegraph2 import _bytecode_tools as bytecode_tools
import textwrap


def make_code(source):
    source = textwrap.dedent(source)
    return compile(source, "<testscript>", "exec", dont_inherit=True)


class TestByteCodeExtractor(unittest.TestCase):
    def test_basic(self):
        code = make_code(
            """\
            import foo

            b = __import__
            c = __name__
            a = b + 42
            """
        )

        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)

        self.assertEqual(names_written, {"foo", "b", "c", "a"})
        self.assertEqual(names_read, {"__import__", "__name__", "b"})

        self.assertEqual(len(imports), 1)

        self.assertEqual(imports[0].import_module, "foo")
        self.assertEqual(imports[0].import_level, 0)
        self.assertEqual(imports[0].star_import, False)
        self.assertEqual(imports[0].import_names, set())
        self.assertEqual(imports[0].is_in_function, False)

    def test_basic_large(self):
        # Test with a large number of names in the local scope before
        # the imported module name, results in slightly different byte code
        names = [f"a{i}" for i in range(1000)]
        prefix = "\n".join(f"            {nm} = 1" for nm in names)
        code = make_code(
            prefix
            + """\

            import foo

            b = __import__
            c = __name__
            a = b + 42
            """
        )

        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)

        self.assertEqual(names_written, {"foo", "b", "c", "a"} | set(names))
        self.assertEqual(names_read, {"__import__", "__name__", "b"})

        self.assertEqual(len(imports), 1)

        self.assertEqual(imports[0].import_module, "foo")
        self.assertEqual(imports[0].import_level, 0)
        self.assertEqual(imports[0].star_import, False)
        self.assertEqual(imports[0].import_names, set())
        self.assertEqual(imports[0].is_in_function, False)

    def test_basic_large_relative(self):
        # Test with a large number of names in the local scope before
        # the imported module name, results in slightly different byte code
        names = [f"a{i}" for i in range(1000)]
        prefix = "\n".join(f"            {nm} = 1" for nm in names)
        code = make_code(
            prefix
            + """\

            from ..foo import bar

            b = __import__
            c = __name__
            a = b + 42
            """
        )

        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)

        self.assertEqual(names_written, {"bar", "b", "c", "a"} | set(names))
        self.assertEqual(names_read, {"__import__", "__name__", "b"})

        self.assertEqual(len(imports), 1)

        self.assertEqual(imports[0].import_module, "foo")
        self.assertEqual(imports[0].import_level, 2)
        self.assertEqual(imports[0].star_import, False)
        self.assertEqual(imports[0].import_names, {"bar"})
        self.assertEqual(imports[0].is_in_function, False)

    def test_import_in_class_large(self):
        # Test with a large number of names in the local scope before
        # the imported module name, results in slightly different byte code
        names = [f"a{i}" for i in range(1000)]
        prefix = "\n".join(f"            {nm} = 1" for nm in names)
        code = make_code(
            prefix
            + """\

            class C:
                import foo

            b = __import__
            c = __name__
            a = b + 42
            """
        )

        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)

        self.assertEqual(len(imports), 1)

        self.assertEqual(imports[0].import_module, "foo")
        self.assertEqual(imports[0].import_level, 0)
        self.assertEqual(imports[0].star_import, False)
        self.assertEqual(imports[0].import_names, set())
        self.assertEqual(imports[0].is_in_function, False)

    def test_import_in_function_large(self):
        # Test with a large number of names in the local scope before
        # the imported module name, results in slightly different byte code
        names = [f"a{i}" for i in range(1000)]
        prefix = "\n".join(f"            {nm} = 1" for nm in names)
        code = make_code(
            prefix
            + """\

            def function():
                import foo

            b = __import__
            c = __name__
            a = b + 42
            """
        )

        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)

        self.assertEqual(len(imports), 1)

        self.assertEqual(imports[0].import_module, "foo")
        self.assertEqual(imports[0].import_level, 0)
        self.assertEqual(imports[0].star_import, False)
        self.assertEqual(imports[0].import_names, set())
        self.assertEqual(imports[0].is_in_function, True)

    def test_basic_larger(self):
        code = make_code(
            f"""\
            from __future__ import print_function

            VALUE = { { v: ((v,)*10,)*10 for v in range(1000) } }

            if __name__ == "__main__":
                import sys
                import os
            """
        )
        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)
        self.assertEqual(len(imports), 3)

        self.assertEqual(imports[0].import_module, "__future__")
        self.assertEqual(imports[0].import_level, 0)
        self.assertEqual(imports[0].star_import, False)
        self.assertEqual(imports[0].import_names, {"print_function"})
        self.assertEqual(imports[0].is_in_function, False)

        self.assertEqual(imports[1].import_module, "sys")
        self.assertEqual(imports[1].import_level, 0)
        self.assertEqual(imports[1].star_import, False)
        self.assertEqual(imports[1].import_names, set())
        self.assertEqual(imports[1].is_in_function, False)

        self.assertEqual(imports[2].import_module, "os")
        self.assertEqual(imports[2].import_level, 0)
        self.assertEqual(imports[2].star_import, False)
        self.assertEqual(imports[2].import_names, set())
        self.assertEqual(imports[2].is_in_function, False)

    def test_nested_imports(self):
        code = make_code(
            """\
            import a

            class C:
                import b

                def method(self):
                    import c

            def func():
                import d

                class C2:
                    import e
            """
        )

        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)

        self.assertEqual(names_written, {"a", "C", "func"})
        self.assertEqual(names_read, set())

        self.assertEqual(len(imports), 5)
        self.assertEqual(
            {item.import_module for item in imports}, {"a", "b", "c", "d", "e"}
        )

        for info in imports:
            with self.subTest(info.import_module):
                self.assertEqual(info.import_level, 0)
                self.assertEqual(info.star_import, False)
                self.assertEqual(info.import_names, set())
                self.assertEqual(
                    info.is_in_function, info.import_module in {"c", "d", "e"}
                )

    def test_import_types(self):
        code = make_code(
            """\
            def func():
                from A import B, C
                import D.E
                from .F import G

                # no star imports in functions

            from a import b, c
            import d.e
            from .f import g
            from h import *
            """
        )

        imports, names_written, names_read = bytecode_tools.extract_bytecode_info(code)

        self.assertEqual(names_written, {"b", "c", "d", "g", "func"})
        self.assertEqual(names_read, set())

        self.assertEqual(len(imports), 7)
        self.assertEqual(
            {item.import_module for item in imports},
            {"a", "d.e", "f", "h", "A", "D.E", "F"},
        )

        for info in imports:
            with self.subTest(info.import_module):
                self.assertEqual(
                    info.import_level, 1 if info.import_module.lower() == "f" else 0
                )

                self.assertEqual(info.star_import, info.import_module == "h")

                if info.import_module == "a":
                    self.assertEqual(info.import_names, {"b", "c"})
                elif info.import_module == "f":
                    self.assertEqual(info.import_names, {"g"})
                elif info.import_module == "A":
                    self.assertEqual(info.import_names, {"B", "C"})
                elif info.import_module == "F":
                    self.assertEqual(info.import_names, {"G"})
                else:
                    self.assertEqual(info.import_names, set())

                self.assertEqual(info.is_in_function, info.import_module.isupper())
                self.assertEqual(info.is_optional, info.import_module.isupper())
                self.assertEqual(info.is_global, info.import_module.islower())
