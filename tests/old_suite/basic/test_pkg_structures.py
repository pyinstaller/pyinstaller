#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Tests - hooks, strange pkg structures, version, icon.
#
# In this test, the *whole* package `pkg1` is replaced by the code and
# content of `pkg2`, while the name `pkg1` is kept. `pkg2` is not
# contained in the frozen exe.
#
# Additionally, the code of `pkg2` has a module `pkg2.b`, which
# resides in file:`pkg2/extra/.py`. So this test checks also if path
# extension is working for this very special case.
#
# The magic for all of this is done in hooks1/hook-pkg1.py.
#
# The In PyInstaller 2.1 this was done by simply replacing the
# code-object and filename in the hook.
# TODO: In modulegraph this does not yet work.
#

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
