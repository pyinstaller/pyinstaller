# Copyright (C) 2009, Lorenzo Berni
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

import os
import glob

def hook(mod):
    global hiddenimports

    modpath = mod.__path__[0]
    hiddenimports = []

    for fn in glob.glob(os.path.join(modpath, '*')):
        if os.path.isdir(fn):
            fn = os.path.basename(fn)
            hiddenimports.append('django.db.backends.' + fn + '.base')

    # Compiler (see class BaseDatabaseOperations)
    hiddenimports.append("django.db.models.sql.compiler")

    return mod

