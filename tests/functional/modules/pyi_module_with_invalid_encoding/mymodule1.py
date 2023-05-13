# NOTE: if you edit this file, be careful not to change the encoding!
#
# The comment line below intentionally contains a non-ASCII character in local encoding and fails to declare the
# encoding using PEP263 encoding header.
#
# problematic character: é (e-acute in ISO-8859-15)
#
# While python is able to load and run the module, retrieving its source code via loader's `get_source`
# method is expected to raise an error:
#
# ```
# import mymodule1
# mymodule1.__loader__.get_source('mymodule1')
# ```
#
# ```
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "<frozen importlib._bootstrap_external>", line 997, in get_source
#   File "<frozen importlib._bootstrap_external>", line 770, in decode_source
# UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 298: invalid continuation byte
# ```

def hello():
    return "hello"
