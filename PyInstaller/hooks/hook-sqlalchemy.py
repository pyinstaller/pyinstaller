#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


from PyInstaller.utils.hooks import exec_statement, is_module_version

# include most common database bindings
# some database bindings are detected and include some
# are not. We should explicitly include database backends.
hiddenimports = ['pysqlite2', 'MySQLdb', 'psycopg2']

# sqlalchemy.dialects package from 0.6 and newer sqlachemy versions
if is_module_version('sqlalchemy', '>=', '0.6'):
    dialects = exec_statement("import sqlalchemy.dialects;print(sqlalchemy.dialects.__all__)")
    dialects = eval(dialects.strip())

    for n in dialects:
        hiddenimports.append("sqlalchemy.dialects." + n)
else:
    # sqlalchemy.databases package from pre 0.6 sqlachemy versions
    databases = exec_statement("import sqlalchemy.databases; print(sqlalchemy.databases.__all__)")
    databases = eval(databases.strip())

    for n in databases:
        hiddenimports.append("sqlalchemy.databases." + n)
