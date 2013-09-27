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
if t1 != e1:
    print('expected: %s' % e1)
    print('     got: %s' % t1)


t2 = b.b_func()
if t2 != e2:
    print('expected: %s' % e2)
    print('     got: %s' % t2)


t3 = notamodule()
if t3 != e3:
    print('expected: %s' % e3)
    print('     got: %s' % t3)
