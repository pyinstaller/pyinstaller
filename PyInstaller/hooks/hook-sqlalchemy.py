#-----------------------------------------------------------------------------
# Copyright (c) 2005-2022, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

import re

from PyInstaller.lib.modulegraph.modulegraph import SourceModule
from PyInstaller.lib.modulegraph.util import guess_encoding
from PyInstaller.utils.hooks import exec_statement, is_module_satisfies, logger

# 'sqlalchemy.testing' causes bundling a lot of unnecessary modules.
excludedimports = ['sqlalchemy.testing']

# Include most common database bindings some database bindings are detected and include some are not. We should
# explicitly include database backends.
hiddenimports = ['pysqlite2', 'MySQLdb', 'psycopg2', 'sqlalchemy.ext.baked']

if is_module_satisfies('sqlalchemy >= 1.4'):
    hiddenimports.append("sqlalchemy.sql.default_comparator")

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


def hook(hook_api):
    """
    SQLAlchemy 0.9 introduced the decorator 'util.dependencies'.  This decorator does imports. E.g.:

            @util.dependencies("sqlalchemy.sql.schema")

    This hook scans for included SQLAlchemy modules and then scans those modules for any util.dependencies and marks
    those modules as hidden imports.
    """

    if not is_module_satisfies('sqlalchemy >= 0.9'):
        return

    # this parser is very simplistic but seems to catch all cases as of V1.1
    depend_regex = re.compile(r'@util.dependencies\([\'"](.*?)[\'"]\)')

    hidden_imports_set = set()
    known_imports = set()
    for node in hook_api.module_graph.iter_graph(start=hook_api.module):
        if isinstance(node, SourceModule) and \
                node.identifier.startswith('sqlalchemy.'):
            known_imports.add(node.identifier)
            # Determine the encoding of the source file.
            with open(node.filename, 'rb') as f:
                encoding = guess_encoding(f)
            # Use that to open the file.
            with open(node.filename, 'r', encoding=encoding) as f:
                for match in depend_regex.findall(f.read()):
                    hidden_imports_set.add(match)

    hidden_imports_set -= known_imports
    if len(hidden_imports_set):
        logger.info("  Found %d sqlalchemy hidden imports", len(hidden_imports_set))
        hook_api.add_imports(*list(hidden_imports_set))
