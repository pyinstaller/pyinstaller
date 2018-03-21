#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# This test code is taken from the example code for the `future` library, with
# a few modifications to allow execution on 32-bit platforms.
# http://python-future.org/overview.html#code-examples

from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import (bytes, str, open, super, range,
                      zip, round, input, int, pow, object)

# Backported Py3 bytes object
b = bytes(b'ABCD')
assert list(b) == [65, 66, 67, 68]
assert repr(b) == "b'ABCD'"
# These raise TypeErrors:
try:
    b + u'EFGH'
except TypeError:
    pass
else:
    assert False, "`bytes + str` did not raise TypeError"

try:
    bytes(b',').join([u'Fred', u'Bill'])
except TypeError:
    pass
else:
    assert False, "`bytes.join([str, str])` did not raise TypeError"

# Backported Py3 str object
s = str(u'ABCD')
assert s != bytes(b'ABCD')
assert isinstance(s.encode('utf-8'), bytes)
assert isinstance(b.decode('utf-8'), str)
assert repr(s) == "'ABCD'"      # consistent repr with Py3 (no u prefix)
# These raise TypeErrors:
try:
    bytes(b'B') in s
except TypeError:
    pass
else:
    assert False, "`bytes in str` did not raise TypeError"

try:
    s.find(bytes(b'A'))
except TypeError:
    pass
else:
    assert False, "`str.find(bytes)` did not raise TypeError"


# New zero-argument super() function:
class VerboseList(list):
    def append(self, item):
        print('Adding an item')
        super().append(item)

# Fix: this fails on 32-bit Python. The traceback::
#
#        E:\pyinstaller>python tests\functional\scripts\pyi_future.py
#     Traceback (most recent call last):
#      File "tests\functional\scripts\pyi_future.py", line 66, in <module>
#        for i in range(10**15)[:10]:
#      File "C:\Users\bjones\Downloads\WinPython-32bit-2.7.10.3\python-2.7.10\lib\site-packages\future\types\newrange.py", line 122, in __getitem__
#        return self.__getitem_slice(index)
#      File "C:\Users\bjones\Downloads\WinPython-32bit-2.7.10.3\python-2.7.10\lib\site-packages\future\types\newrange.py", line 134, in __getitem_slice
#        scaled_indices = (self._step * n for n in slce.indices(self._len))
#     OverflowError: cannot fit 'long' into an index-sized integer
#
# So, pick a smaller (32-bit capable) range to iterate over.
#
# New iterable range object with slicing support
for i in range(2**30)[:10]:
    pass

# Other iterators: map, zip, filter
my_iter = zip(range(3), ['a', 'b', 'c'])
assert my_iter != list(my_iter)

# The round() function behaves as it does in Python 3, using
# "Banker's Rounding" to the nearest even last digit:
assert round(0.1250, 2) == 0.12

# pow() supports fractional exponents of negative numbers like in Py3:
z = pow(-1, 0.5)

# Compatible output from isinstance() across Py2/3:
assert isinstance(2**64, int)        # long integers
assert isinstance(u'blah', str)
assert isinstance('blah', str)       # only if unicode_literals is in effect

# Py3-style iterators written as new-style classes (subclasses of
# future.types.newobject) are automatically backward compatible with Py2:
class Upper(object):
    def __init__(self, iterable):
        self._iter = iter(iterable)
    def __next__(self):                 # note the Py3 interface
        return next(self._iter).upper()
    def __iter__(self):
        return self
assert list(Upper('hello')) == list('HELLO')
