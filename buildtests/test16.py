# Copyright (C) 2007, Matteo Bertini
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

print "test16 imp.find_module"

import sys
import imp

modname = "test15"

for p in sys.path:
    try:
        i = imp.find_module(modname, [p])
    except ImportError:
        continue
else:
    raise ImportError("Couldn't find the real '%s' module" % modname)
    # as in setuptools/site.py

print "test16 DONE"

