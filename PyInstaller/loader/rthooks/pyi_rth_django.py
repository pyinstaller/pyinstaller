#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This Django rthook was tested with Django 1.8.3.


import django.core.management
import django.utils.autoreload


def _get_commands():
    # Django groupss commands by app.
    # This returns static dict() as it is for django 1.8 and the default project.
    commands = {
         'changepassword': 'django.contrib.auth',
         'check': 'django.core',
         'clearsessions': 'django.contrib.sessions',
         'collectstatic': 'django.contrib.staticfiles',
         'compilemessages': 'django.core',
         'createcachetable': 'django.core',
         'createsuperuser': 'django.contrib.auth',
         'dbshell': 'django.core',
         'diffsettings': 'django.core',
         'dumpdata': 'django.core',
         'findstatic': 'django.contrib.staticfiles',
         'flush': 'django.core',
         'inspectdb': 'django.core',
         'loaddata': 'django.core',
         'makemessages': 'django.core',
         'makemigrations': 'django.core',
         'migrate': 'django.core',
         'runfcgi': 'django.core',
         'runserver': 'django.contrib.staticfiles',
         'shell': 'django.core',
         'showmigrations': 'django.core',
         'sql': 'django.core',
         'sqlall': 'django.core',
         'sqlclear': 'django.core',
         'sqlcustom': 'django.core',
         'sqldropindexes': 'django.core',
         'sqlflush': 'django.core',
         'sqlindexes': 'django.core',
         'sqlmigrate': 'django.core',
         'sqlsequencereset': 'django.core',
         'squashmigrations': 'django.core',
         'startapp': 'django.core',
         'startproject': 'django.core',
         'syncdb': 'django.core',
         'test': 'django.core',
         'testserver': 'django.core',
         'validate': 'django.core'
    }
    return commands


_old_restart_with_reloader = django.utils.autoreload.restart_with_reloader


def _restart_with_reloader(*args):
    import sys
    a0 = sys.argv.pop(0)
    try:
        return _old_restart_with_reloader(*args)
    finally:
        sys.argv.insert(0, a0)


# Override get_commands() function otherwise the app will complain that
# there are no commands.
django.core.management.get_commands = _get_commands
# Override restart_with_reloader() function otherwise the app might
# complain that some commands do not exist. e.g. runserver.
django.utils.autoreload.restart_with_reloader = _restart_with_reloader
