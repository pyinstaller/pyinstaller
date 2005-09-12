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
import sys, os
import test6x
print "test6x.x is", test6x.x
txt = """\
x = %d
""" % (test6x.x + 1)
if hasattr(sys, 'frozen'):
    open(os.path.join(os.path.dirname(sys.executable), 'test6x.py'), 'w').write(txt)
else:
    open(test6x.__file__, 'w').write(txt)
reload(test6x)
print "test6x.x is now", test6x.x

