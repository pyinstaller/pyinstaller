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
print "test4 - unbufferred"
print "type: 123456<enter>"
print "should see: 12345"
print "type: <enter>"
print "if unbuffered should see: 6"
print "if NOT unbuffered, should see nothing"
print "Q to quit"
import sys
while 1:
    data = sys.stdin.read(5)
    sys.stdout.write(data)
    if 'Q' in data:
        break
print "test4i - done"
