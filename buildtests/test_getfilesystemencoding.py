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

print "test_getfilesystemencoding"

import sys
if sys.version_info[:2] >= (2, 5):
    import subprocess
    import email

    assert type(email.Header) == email.LazyImporter

    pyexe = open("python_exe.build").readline().strip()
    out = subprocess.Popen([pyexe, '-c', 'import sys; print sys.getfilesystemencoding()'],
                           stdout=subprocess.PIPE).stdout.read().strip()
    assert str(sys.getfilesystemencoding()) == out, (str(sys.getfilesystemencoding()), out)

    print "test_getfilesystemencoding DONE"
else:
    print "Python < 2.5 test14 skipped"
