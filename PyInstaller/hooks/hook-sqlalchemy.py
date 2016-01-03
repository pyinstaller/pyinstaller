#-----------------------------------------------------------------------------
# Copyright (c) 2005-2016, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import exec_statement, is_module_satisfies

# include most common database bindings
# some database bindings are detected and include some
# are not. We should explicitly include database backends.
hiddenimports = ['pysqlite2', 'MySQLdb', 'psycopg2']

# In SQLAlchemy >= 0.6, the "sqlalchemy.dialects" package provides dialects.
if is_module_satisfies('sqlalchemy >= 0.6'):
    dialects = exec_statement("import sqlalchemy.dialects;print(sqlalchemy.dialects.__all__)")
    dialects = eval(dialects.strip())

    for n in dialects:
        hiddenimports.append("sqlalchemy.dialects." + n)
# In SQLAlchemy <= 0.5, the "sqlalchemy.databases" package provides dialects.
else:
    databases = exec_statement("import sqlalchemy.databases; print(sqlalchemy.databases.__all__)")
    databases = eval(databases.strip())

    for n in databases:
        hiddenimports.append("sqlalchemy.databases." + n)
