# Copyright (C) 2009, Lorenzo Berni
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


def _find_commands(_):
    return """cleanup compilemessages createcachetable dbshell shell runfcgi runserver startproject""".split()

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
