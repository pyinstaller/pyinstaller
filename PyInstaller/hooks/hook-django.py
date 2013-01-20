#
# Copyright (C) 2013, Martin Zibricky
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
