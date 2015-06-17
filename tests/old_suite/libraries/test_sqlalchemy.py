#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# sqlalchemy hook test

# The hook behaviour is to include with sqlalchemy all installed database
# backends.
import sqlalchemy

# This import was known to fail with sqlalchemy 0.9.1
import sqlalchemy.ext.declarative


# import mysql and postgreql bindings
__import__('MySQLdb')
__import__('psycopg2')
