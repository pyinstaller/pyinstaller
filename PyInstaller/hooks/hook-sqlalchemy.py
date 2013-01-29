#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


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
