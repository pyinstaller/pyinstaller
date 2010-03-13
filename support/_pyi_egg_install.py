#!/usr/bin/env python
#
# Make .eggs and zipfiles available at runtime
#
# Copyright (C) 2010 Giovanni Bajo <rasky@develer.com>
#
# This file is part of PyInstaller <http://www.pyinstaller.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition to the permissions in the GNU General Public License, the
# authors give you unlimited permission to link or embed the compiled
# version of this file into combinations with other programs, and to
# distribute those combinations without any restriction coming from the
# use of this file. (The General Public License restrictions do apply in
# other respects; for example, they cover modification of the file, and
# distribution when not linked into a combine executable.)
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import os

d = "eggs"
if "_MEIPASS2" in os.environ:
    d = os.path.join(os.environ["_MEIPASS2"], d)
else:
    d = os.path.join(os.path.dirname(sys.argv[0]), d)

for fn in os.listdir(d):
    sys.path.append(os.path.join(d, fn))


