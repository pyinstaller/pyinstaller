import ast
import unittest

from modulegraph2 import _ast_tools as ast_tools
import textwrap


def make_ast(source):
    source = textwrap.dedent(source)
    return compile(
        source, "<testscript>", "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True
    )


class TestAstExtractor(unittest.TestCase):
    def test_toplevel_imports(self):
        ast = make_ast(
            """\
            # Basic import
            import sys
            import a, b, c

            # Absolute 'from' imports
            from d import *
            from e import f
            from g import h, i
            from j import (k, l, m)

            # Relative 'from' imports
            from . import o
            from .. import p
            from ..q import r, s
            from ...t.u import v
            from .w import *
            """
        )

        imports = list(ast_tools.extract_ast_info(ast))
        self.assertEqual(len(imports), 13)

        for info in imports:
            self.assertEqual(info.is_in_function, False)
            self.assertEqual(info.is_in_conditional, False)
            self.assertEqual(info.is_in_tryexcept, False)
            self.assertEqual(info.is_optional, False)
            self.assertEqual(info.is_global, True)

        # import sys
        self.assertEqual(imports[0].import_module, "sys")
        self.assertEqual(imports[0].import_level, 0)
        self.assertEqual(imports[0].import_names, set())
        self.assertEqual(imports[0].star_import, False)

        # import a, b, c
        self.assertEqual(imports[1].import_module, "a")
        self.assertEqual(imports[1].import_level, 0)
        self.assertEqual(imports[1].import_names, set())
        self.assertEqual(imports[1].star_import, False)

        self.assertEqual(imports[2].import_module, "b")
        self.assertEqual(imports[2].import_level, 0)
        self.assertEqual(imports[2].import_names, set())
        self.assertEqual(imports[2].star_import, False)

        self.assertEqual(imports[3].import_module, "c")
        self.assertEqual(imports[3].import_level, 0)
        self.assertEqual(imports[3].import_names, set())
        self.assertEqual(imports[3].star_import, False)

        # from d import *
        self.assertEqual(imports[4].import_module, "d")
        self.assertEqual(imports[4].import_level, 0)
        self.assertEqual(imports[4].import_names, set())
        self.assertEqual(imports[4].star_import, True)

        # from e import f
        self.assertEqual(imports[5].import_module, "e")
        self.assertEqual(imports[5].import_level, 0)
        self.assertEqual(imports[5].import_names, {"f"})
        self.assertEqual(imports[5].star_import, False)

        # from g import h, i
        self.assertEqual(imports[6].import_module, "g")
        self.assertEqual(imports[6].import_level, 0)
        self.assertEqual(imports[6].import_names, {"h", "i"})
        self.assertEqual(imports[6].star_import, False)

        # from j import (k, l, m)
        self.assertEqual(imports[7].import_module, "j")
        self.assertEqual(imports[7].import_level, 0)
        self.assertEqual(imports[7].import_names, {"k", "l", "m"})
        self.assertEqual(imports[7].star_import, False)

        # from . import o
        self.assertEqual(imports[8].import_module, "")
        self.assertEqual(imports[8].import_level, 1)
        self.assertEqual(imports[8].import_names, {"o"})
        self.assertEqual(imports[8].star_import, False)

        # from .. import p
        self.assertEqual(imports[9].import_module, "")
        self.assertEqual(imports[9].import_level, 2)
        self.assertEqual(imports[9].import_names, {"p"})
        self.assertEqual(imports[9].star_import, False)

        # from ..q import r, s
        self.assertEqual(imports[10].import_module, "q")
        self.assertEqual(imports[10].import_level, 2)
        self.assertEqual(imports[10].import_names, {"r", "s"})
        self.assertEqual(imports[10].star_import, False)

        # from ...t.u import v
        self.assertEqual(imports[11].import_module, "t.u")
        self.assertEqual(imports[11].import_level, 3)
        self.assertEqual(imports[11].import_names, {"v"})
        self.assertEqual(imports[11].star_import, False)

        # from .w import *
        self.assertEqual(imports[12].import_module, "w")
        self.assertEqual(imports[12].import_level, 1)
        self.assertEqual(imports[12].import_names, set())
        self.assertEqual(imports[12].star_import, True)

    def test_import_in_block(self):
        ast = make_ast(
            """\
            while True:
                import a

            class C:
                import b

            for i in S:
                import c
            """
        )

        imports = list(ast_tools.extract_ast_info(ast))
        self.assertEqual(len(imports), 3)

        for info in imports:
            self.assertEqual(info.import_level, 0)
            self.assertEqual(info.import_names, set())
            self.assertEqual(info.star_import, False)
            self.assertEqual(info.is_in_function, False)
            self.assertEqual(info.is_in_conditional, False)
            self.assertEqual(info.is_in_tryexcept, False)
            self.assertEqual(info.is_optional, False)
            self.assertEqual(info.is_global, True)

        self.assertEqual(imports[0].import_module, "a")
        self.assertEqual(imports[1].import_module, "b")
        self.assertEqual(imports[2].import_module, "c")

    def test_import_in_function(self):
        ast = make_ast(
            """\
            def function1():
                import a

            while True:
                def function2():
                    import b

            import c
            """
        )

        imports = list(ast_tools.extract_ast_info(ast))
        self.assertEqual(len(imports), 3)

        for info in imports:
            self.assertEqual(info.import_level, 0)
            self.assertEqual(info.import_names, set())
            self.assertEqual(info.star_import, False)
            self.assertEqual(info.is_in_function, info.import_module != "c")
            self.assertEqual(info.is_in_conditional, False)
            self.assertEqual(info.is_in_tryexcept, False)
            self.assertEqual(info.is_optional, info.import_module != "c")
            self.assertEqual(info.is_global, info.import_module == "c")

        self.assertEqual({n.import_module for n in imports}, {"a", "b", "c"})

    def test_import_in_ifstatement(self):
        ast = make_ast(
            """\
            if x == y:
                import a

            else:
                import b

            import c
            """
        )

        imports = list(ast_tools.extract_ast_info(ast))
        self.assertEqual(len(imports), 3)

        for info in imports:
            self.assertEqual(info.import_level, 0)
            self.assertEqual(info.import_names, set())
            self.assertEqual(info.star_import, False)
            self.assertEqual(info.is_in_function, False)
            self.assertEqual(info.is_in_conditional, info.import_module != "c")
            self.assertEqual(info.is_in_tryexcept, False)
            self.assertEqual(info.is_optional, info.import_module != "c")
            self.assertEqual(info.is_global, True)

        self.assertEqual({n.import_module for n in imports}, {"a", "b", "c"})

    def test_import_in_tryexcept(self):
        ast = make_ast(
            """\
            try:
                import a

            except:
                import b

            finally:
                1+2
                import c


            try:
               1/0

            except:
                pass
            else:
                import d

            import e
            """
        )

        imports = list(ast_tools.extract_ast_info(ast))
        self.assertEqual(len(imports), 5)

        for info in imports:
            with self.subTest(info.import_module):
                self.assertEqual(info.import_level, 0)
                self.assertEqual(info.import_names, set())
                self.assertEqual(info.star_import, False)
                self.assertEqual(info.is_in_function, False)
                self.assertEqual(info.is_in_conditional, False)

                # 'import c' is executed unconditionally, hence is not marked as
                # inside a try-except statement.
                self.assertEqual(
                    info.is_in_tryexcept, info.import_module not in {"c", "e"}
                )
                self.assertEqual(info.is_optional, info.import_module not in {"c", "e"})
                self.assertEqual(info.is_global, True)

        self.assertEqual({n.import_module for n in imports}, {"a", "b", "c", "d", "e"})

    def test_recursion(self):
        list_value = list(range(400))
        source = f"l = {list_value}\nimport a"
        ast = make_ast(source)
        imports = list(ast_tools.extract_ast_info(ast))
        self.assertEqual(len(imports), 1)

        self.assertEqual(imports[0].import_module, "a")
        self.assertEqual(imports[0].import_level, 0)
        self.assertEqual(imports[0].import_names, set())
        self.assertEqual(imports[0].star_import, False)
        self.assertEqual(imports[0].is_in_function, False)
        self.assertEqual(imports[0].is_in_conditional, False)
        self.assertEqual(imports[0].is_in_tryexcept, False)

    def test_combined(self):
        ast = make_ast(
            """\
            import a

            def fun(self):
                import b

                if a == b:
                    import c

                else:
                    import d

                import e

                try:
                    import f

                except:
                    if e == f:
                        import g

                finally:
                     def subfun():
                         import h

                     import i

                if i == h:
                    import j

                    if j == i:
                        import k

                    else:
                        import l

                    import m

                    try:
                        import o

                    except:
                        import p

                    else:
                        import q

            if a == b:
                import r

                def fun2():
                    import s

                    if r == s:
                        import t

                    import u

                try:
                    import v

                    try:
                        import w

                    finally:
                        import x

                    def fun3(self):
                        import y

                finally:
                    import z
            """
        )
        imports = list(ast_tools.extract_ast_info(ast))
        imports.sort(key=lambda x: x.import_module)

        EXPECTED = {
            # NAME: (IN_DEF, IN_IF, IN_TRY)
            "a": (False, False, False),
            "b": (True, False, False),
            "c": (True, True, False),
            "d": (True, True, False),
            "e": (True, False, False),
            "f": (True, False, True),
            "g": (True, True, True),
            "h": (True, False, False),
            "i": (True, False, False),
            "j": (True, True, False),
            "k": (True, True, False),
            "l": (True, True, False),
            "m": (True, True, False),
            "o": (True, True, True),
            "p": (True, True, True),
            "q": (True, True, True),
            "r": (False, True, False),
            "s": (True, True, False),
            "t": (True, True, False),
            "u": (True, True, False),
            "v": (False, True, True),
            "w": (False, True, True),
            "x": (False, True, True),
            "y": (True, True, True),
            "z": (False, True, False),
        }
        self.assertEqual(len(imports), len(EXPECTED))

        for info in imports:
            with self.subTest(info.import_module):
                in_def, in_if, in_try = EXPECTED[info.import_module]

                self.assertEqual(info.import_level, 0)
                self.assertEqual(info.import_names, set())
                self.assertEqual(info.star_import, False)
                self.assertEqual(info.is_in_function, in_def)
                self.assertEqual(info.is_in_conditional, in_if)
                self.assertEqual(info.is_in_tryexcept, in_try)
                self.assertEqual(info.is_optional, in_def or in_if or in_try)
                self.assertEqual(info.is_global, not in_def)

    def test_import_renames(self):
        ast = make_ast(
            """\
            import a as A
            import b as B, c as C

            from d import e as E
            from f import g as G, h as H

            from .i import j as J

            import n
            from m import o
            """
        )

        imports = list(ast_tools.extract_ast_info(ast))
        self.assertEqual(len(imports), 8)

        self.assertEqual(imports[0].import_module, "a")
        self.assertEqual(imports[0].import_module.asname, "A")

        self.assertEqual(imports[1].import_module, "b")
        self.assertEqual(imports[1].import_module.asname, "B")
        self.assertEqual(imports[2].import_module, "c")
        self.assertEqual(imports[2].import_module.asname, "C")

        self.assertEqual(imports[3].import_module, "d")
        self.assertEqual(imports[3].import_module.asname, None)
        self.assertEqual(imports[3].import_names, {"e"})
        self.assertEqual(list(imports[3].import_names)[0].asname, "E")

        self.assertEqual(imports[4].import_module, "f")
        self.assertEqual(imports[4].import_module.asname, None)
        self.assertEqual(imports[4].import_names, {"g", "h"})
        self.assertTrue(all(n.upper() == n.asname for n in imports[4].import_names))

        self.assertEqual(imports[5].import_module, "i")
        self.assertEqual(imports[5].import_module.asname, None)
        self.assertEqual(imports[5].import_names, {"j"})
        self.assertEqual(list(imports[5].import_names)[0].asname, "J")

        self.assertEqual(imports[6].import_module, "n")
        self.assertEqual(imports[6].import_module.asname, None)

        self.assertEqual(imports[7].import_module, "m")
        self.assertEqual(imports[7].import_module.asname, None)
        self.assertEqual(imports[7].import_names, {"o"})
        self.assertEqual(list(imports[7].import_names)[0].asname, None)
