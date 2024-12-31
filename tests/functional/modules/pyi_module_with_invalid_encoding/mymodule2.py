# problematic character: é (e-acute in ISO-8859-15)
#
# NOTE: if you edit this file, be careful not to change the encoding!
#
# The first comment line in this file intentionally contains a non-ASCII character in local encoding and fails to
# declare the encoding using PEP263 encoding header.
#
# While python is able to load and run the module, retrieving its source code via loader's `get_source`
# method is expected to raise an error:
#
# ```
# import mymodule2
# mymodule2.__loader__.get_source('mymodule2')
# ```
#
# ```
# Traceback (most recent call last):
#   File "/usr/lib64/python3.11/tokenize.py", line 334, in find_cookie
#     line_string = line.decode('utf-8')
#                   ^^^^^^^^^^^^^^^^^^^^
# UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 25: invalid continuation byte
#
# During handling of the above exception, another exception occurred:
#
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "<frozen importlib._bootstrap_external>", line 997, in get_source
#   File "<frozen importlib._bootstrap_external>", line 768, in decode_source
#   File "/usr/lib64/python3.11/tokenize.py", line 375, in detect_encoding
#     encoding = find_cookie(first)
#                ^^^^^^^^^^^^^^^^^^
#   File "/usr/lib64/python3.11/tokenize.py", line 339, in find_cookie
#     raise SyntaxError(msg)
# SyntaxError: invalid or missing encoding declaration
# ```
#
# In contrast to `mymodule1` example, this example triggers a `SyntaxError` due to offending character appearing in the
# first line of the file, and thus breaking the scan for PEP263 encoding header.

def hello():
    return "hello"
