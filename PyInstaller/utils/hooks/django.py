# ----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# ----------------------------------------------------------------------------
import os

from ..hooks import eval_script
from ...utils import misc


__all__ = [
    'django_dottedstring_imports', 'django_find_root_dir'
]


def django_dottedstring_imports(django_root_dir):
    """
    Get all the necessary Django modules specified in settings.py.

    In the settings.py the modules are specified in several variables
    as strings.
    """
    pths = []
    # Extend PYTHONPATH with parent dir of django_root_dir.
    pths.append(misc.get_path_to_toplevel_modules(django_root_dir))
    # Extend PYTHONPATH with django_root_dir.
    # Often, Django users do not specify absolute imports in the settings
    # module.
    pths.append(django_root_dir)

    default_settings_module = os.path.basename(django_root_dir) + '.settings'
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', default_settings_module)
    env = {'DJANGO_SETTINGS_MODULE': settings_module,
           'PYTHONPATH': os.pathsep.join(pths)}
    ret = eval_script('django_import_finder.py', env=env)

    return ret


def django_find_root_dir():
    """
    Return path to directory (top-level Python package) that contains main django
    files. Return None if no directory was detected.

    Main Django project directory contain files like '__init__.py', 'settings.py'
    and 'url.py'.

    In Django 1.4+ the script 'manage.py' is not in the directory with 'settings.py'
    but usually one level up. We need to detect this special case too.
    """
    # 'PyInstaller.config' cannot be imported as other top-level modules.
    from ...config import CONF
    # Get the directory with manage.py. Manage.py is supplied to PyInstaller as the
    # first main executable script.
    manage_py = CONF['main_script']
    manage_dir = os.path.dirname(os.path.abspath(manage_py))

    # Get the Django root directory. The directory that contains settings.py and url.py.
    # It could be the directory containing manage.py or any of its subdirectories.
    settings_dir = None
    files = set(os.listdir(manage_dir))
    if ('settings.py' in files or 'settings' in files) and 'urls.py' in files:
        settings_dir = manage_dir
    else:
        for f in files:
            if os.path.isdir(os.path.join(manage_dir, f)):
                subfiles = os.listdir(os.path.join(manage_dir, f))
                # Subdirectory contains critical files.
                if ('settings.py' in subfiles or 'settings' in subfiles) and 'urls.py' in subfiles:
                    settings_dir = os.path.join(manage_dir, f)
                    break  # Find the first directory.

    return settings_dir
