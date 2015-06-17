#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# PyInstaller did not included module 'sqlite3.dump'.
import sqlite3


conn = sqlite3.connect(':memory:')
csr = conn.cursor()
csr.execute('CREATE TABLE Example (id)')


# Only Python 2.6+ has attribute 'iterdump'.
if hasattr(conn, 'iterdump'):
    for line in conn.iterdump():
         print(line)
