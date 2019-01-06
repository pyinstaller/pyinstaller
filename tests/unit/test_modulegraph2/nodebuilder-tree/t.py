import ast

with open("complex_source.py") as fp:
    s = fp.read()

print(compile(s, "<script>", "exec", flags=ast.PyCF_ONLY_AST, dont_inherit=True))
