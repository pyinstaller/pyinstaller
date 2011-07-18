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
import data6
print "data6.x is", data6.x
txt = """\
x = %d
""" % (data6.x + 1)
if hasattr(sys, 'frozen'):
    open(os.path.join(os.path.dirname(sys.executable), 'data6.py'), 'w').write(txt)
else:
    open(data6.__file__, 'w').write(txt)
reload(data6)
print "data6.x is now", data6.x
