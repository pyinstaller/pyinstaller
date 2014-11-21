#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import sys

d = sys._MEIPASS

import django.core.management
import django.utils.autoreload


def _setup_environ(settings_mod, original_settings_path=None):
    project_name = settings_mod.__name__.split(".")[0]
    settings_name = "settings"
    if original_settings_path:
        os.environ['DJANGO_SETTINGS_MODULE'] = original_settings_path
    else:
        os.environ['DJANGO_SETTINGS_MODULE'] = '%s.%s' % (project_name, settings_name)
    project_module = __import__(project_name, {}, {}, [''])
    return d


def _find_commands(path):
    (head, management_dir) = os.path.split(path)
    if head.endswith(os.path.join('django', 'core')) :
        return """compilemessages createcachetable dbshell shell runfcgi runserver""".split()
    elif head.endswith(os.path.join('django', 'contrib', 'staticfiles')):
        return """runserver"""           
    else :
        return []

old_restart_with_reloader = django.utils.autoreload.restart_with_reloader


def _restart_with_reloader(*args):
    import sys
    a0 = sys.argv.pop(0)
    try:
        return old_restart_with_reloader(*args)
    finally:
        sys.argv.insert(0, a0)


django.core.management.setup_environ = _setup_environ
django.core.management.find_commands = _find_commands
django.utils.autoreload.restart_with_reloader = _restart_with_reloader
