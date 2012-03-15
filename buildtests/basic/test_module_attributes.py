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


# Compare attributes of cElementTree module from frozen executable
# with cElementTree module from standard python.


import os
import sys
import subprocess
import xml.etree.ElementTree as ET
import xml.etree.cElementTree as cET


print "#" * 50
print "xml.etree.ElementTree", dir(ET)
print "#" * 50


if hasattr(sys, 'frozen'):
    # In frozen mode current working directory is the path with final executable.
    pyexe_file = os.path.join('..', '..', 'python_exe.build')
else:
    pyexe_file = 'python_exe.build'


pyexe = open(pyexe_file).readline().strip()


frozen_attribs = str(dir(cET))
attribs = subprocess.Popen([pyexe, '-c',
        'import xml.etree.cElementTree as cET; print dir(cET)'],
        stdout=subprocess.PIPE, shell=False).stdout.read().strip()


# Compare attributes of frozen module with unfronzen module.
if not frozen_attribs == attribs:
    raise SystemExit()
