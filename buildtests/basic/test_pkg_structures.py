# Copyright (C) 2005, Giovanni Bajo
# Based on previous work under copyright (c) 2001, 2002 McMillan Enterprises, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


# Tests - hooks, strange pkg structures, version, icon.


e1 = 'a_func from pkg2.a'
e2 = 'b_func from pkg2.b (pkg2/extra/b.py)'
e3 = 'notamodule from pkg2.__init__'


from pkg1 import *


t1 = a.a_func()
if t1 != e1:
    print "expected:", e1
    print "     got:", t1


t2 = b.b_func()
if t2 != e2:
    print "expected:", e2
    print "     got:", t2


t3 = notamodule()
if t3 != e3:
    print "expected:", e3
    print "     got:", t3
