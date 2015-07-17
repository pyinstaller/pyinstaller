#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# Tested with django 1.8.


import glob
import os
from PyInstaller import log as logging
from PyInstaller.utils.hooks.hookutils import django_find_root_dir, django_dottedstring_imports, \
        collect_data_files, collect_submodules


logger = logging.getLogger(__name__)

hiddenimports = []


root_dir = django_find_root_dir()
if root_dir:
    logger.info('Django root directory %s', root_dir)
    # Include imports from the mysite.settings.py module.
    settings_py_imports = django_dottedstring_imports(root_dir)
    # Include all submodules of all imports detected in mysite.settings.py.
    for submod in settings_py_imports:
        hiddenimports += collect_submodules(submod)
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
    # Django hiddenimports from the standard Python library.
    # TODO there is some import magic in the 'six' module.
    hiddenimports += [
            'http.cookies',
            'html.parser',
    ]

    # Include django data files - localizations, etc.
    datas = collect_data_files('django')

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
    logger.warn('No django root directory could be found!')
