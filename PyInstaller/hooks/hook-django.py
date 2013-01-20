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


import os
from PyInstaller import log as logging
from PyInstaller.hooks.hookutils import django_find_root_dir, django_dottedstring_imports


logger = logging.getLogger(__name__)


root_dir = django_find_root_dir()
if root_dir:
    logger.info('Django root directory %s', root_dir)
    hiddenimports = django_dottedstring_imports(root_dir)
    # Include main django modules - settings.py, urls.py, wsgi.py.
    package_name = os.path.basename(root_dir)
    hiddenimports += [
            package_name + '.settings',
            package_name + '.urls',
            package_name + '.wsgi',
    ]
else:
    logger.warn('No django root directory could be found!')

