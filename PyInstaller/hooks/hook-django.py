#-----------------------------------------------------------------------------
# Copyright (c) 2005-2020, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------


# Tested with django 2.2


import sys
import glob
import os
from PyInstaller import log as logging
from PyInstaller.utils.hooks import (
    django_find_root_dir, django_dottedstring_imports, collect_all,
    collect_submodules, collect_data_files, get_module_file_attribute,
    get_module_attribute)


logger = logging.getLogger(__name__)

datas, binaries, hiddenimports = collect_all('django')


root_dir = django_find_root_dir()
if root_dir:
    logger.info('Django root directory %s', root_dir)
    # Include imports from the mysite.settings.py module.
    settings_py_imports = django_dottedstring_imports(root_dir)
    # Include all submodules of all imports detected in mysite.settings.py.
    for submod in settings_py_imports:
        hiddenimports.append(submod)
        hiddenimports += collect_submodules(submod)
    # Include main django modules - settings.py, urls.py, wsgi.py.
    # Without them the django server won't run.
    package_name = os.path.basename(root_dir)
    default_settings_module = f'{package_name}.settings'
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', default_settings_module)
    hiddenimports += [
            # TODO Consider including 'mysite.settings.py' in source code as a data files.
            #      Since users might need to edit this file.
            settings_module,
            package_name + '.urls',
            package_name + '.wsgi',
    ]
    # Django hiddenimports from the standard Python library.
    hiddenimports += [
        'http.cookies',
        'html.parser',
    ]

    # Bundle django DB schema migration scripts as data files.
    # They are necessary for some commands.
    logger.info('Collecting Django migration scripts.')
    migration_modules = [
             'django.conf.app_template.migrations',
             'django.contrib.admin.migrations',
             'django.contrib.auth.migrations',
             'django.contrib.contenttypes.migrations',
             'django.contrib.flatpages.migrations',
             'django.contrib.redirects.migrations',
             'django.contrib.sessions.migrations',
             'django.contrib.sites.migrations',
    ]
    # Include migration scripts of Django-based apps too.
    installed_apps = eval(get_module_attribute(settings_module, 'INSTALLED_APPS'))
    migration_modules.extend(set(app + '.migrations' for app in installed_apps))
    # Copy migration files.
    for mod in migration_modules:
        mod_name, bundle_name = mod.split('.', 1)
        mod_dir = os.path.dirname(get_module_file_attribute(mod_name))
        bundle_dir = bundle_name.replace('.', os.sep)
        pattern = os.path.join(mod_dir, bundle_dir, '*.py')
        files = glob.glob(pattern)
        for f in files:
            datas.append((f, os.path.join(mod_name, bundle_dir)))

    # Include data files from your Django project found in your django root package.
    datas += collect_data_files(package_name)

    # Include database file if using sqlite. The sqlite database is usually next to the manage.py script.
    root_dir_parent = os.path.dirname(root_dir)
    # TODO Add more patterns if necessary.
    _patterns = ['*.db', 'db.*']
    for p in _patterns:
        files = glob.glob(os.path.join(root_dir_parent, p))
        for f in files:
            # Place those files next to the executable.
            datas.append((f, '.'))


else:
    logger.warning('No django root directory could be found!')
