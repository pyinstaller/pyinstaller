#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Tests - hooks, strange pkg structures, version, icon.


e1 = 'a_func from pkg2.a'
e2 = 'b_func from pkg2.b (pkg2/extra/b.py)'
e3 = 'notamodule from pkg2.__init__'


from pkg1 import *

t1 = a.a_func()
assert t1 == e1, 'expected %s, got %s' % (e1, t1)

t2 = b.b_func()
assert t2 == e2, 'expected %s, got %s' % (e2, t2)

t3 = notamodule()
assert t3 == e3, 'expected %s, got %s' % (e3, t3)
