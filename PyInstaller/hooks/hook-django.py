#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Tested with django 1.4.


import os
from PyInstaller import log as logging
from PyInstaller.hooks.hookutils import django_find_root_dir, django_dottedstring_imports, \
        collect_data_files


logger = logging.getLogger(__name__)


root_dir = django_find_root_dir()
if root_dir:
    logger.info('Django root directory %s', root_dir)
    hiddenimports = django_dottedstring_imports(root_dir)
    # Include main django modules - settings.py, urls.py, wsgi.py.
    # Without them the django server won't run.
    package_name = os.path.basename(root_dir)
    hiddenimports += [
            # TODO Consider including 'mysite.settings.py' in source code as a data files.
            #      Since users might need to edit this file.
            package_name + '.settings',
            package_name + '.urls',
            package_name + '.wsgi',
    ]
    # Include some hidden modules that are not imported directly in django.
    hiddenimports += [
            'django.template.defaultfilters',
            'django.template.defaulttags',
            'django.template.loader_tags',
    ]
    # Other hidden imports to get Django example startproject working.
    hiddenimports += [
            'django.contrib.messages.storage.fallback',
    ]
    # Include django data files - localizations, etc.
    datas = collect_data_files('django')

    # Include data files from your Django project found in your django root package.
    datas += collect_data_files(package_name)

else:
    logger.warn('No django root directory could be found!')
