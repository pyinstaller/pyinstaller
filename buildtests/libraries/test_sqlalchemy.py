# sqlalchemy hook test

# The hook behaviour is to include with sqlalchemy all installed database
# backends.
import sqlalchemy


# import mysql and postgreql bindings
__import__('MySQLdb')
__import__('psycopg2')
