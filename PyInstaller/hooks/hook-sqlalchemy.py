# Copyright (C) 2009, Giovanni Bajo
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

# Contributed by Greg Copeland

from PyInstaller.hooks.hookutils import exec_statement

# include most common database bindings
# some database bindings are detected and include some
# are not. We should explicitly include database backends.
hiddenimports = ['pysqlite2', 'MySQLdb', 'psycopg2']

# sqlalchemy.databases package from pre 0.6 sqlachemy versions
databases = exec_statement("import sqlalchemy.databases;print sqlalchemy.databases.__all__")
databases = eval(databases.strip())

for n in databases:
    hiddenimports.append("sqlalchemy.databases." + n)

# sqlalchemy.dialects package from 0.6 and newer sqlachemy versions
version = exec_statement('import sqlalchemy; print sqlalchemy.__version__')
is_alch06 = version >= '0.6'

if is_alch06:
    dialects = exec_statement("import sqlalchemy.dialects;print sqlalchemy.dialects.__all__")
    dialects = eval(dialects.strip())

    for n in databases:
        hiddenimports.append("sqlalchemy.dialects." + n)
