#
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


import PyInstaller.compat as compat
from hookutils import logger

if not compat.getenv("DJANGO_SETTINGS_MODULE"):
    compat.setenv("DJANGO_SETTINGS_MODULE", "settings")

from django.conf import settings

hiddenimports = (list(settings.AUTHENTICATION_BACKENDS) +
                 [settings.DEFAULT_FILE_STORAGE] +
                 list(settings.FILE_UPLOAD_HANDLERS) +
                 list(settings.INSTALLED_APPS) +
                 list(settings.MIDDLEWARE_CLASSES) +
                 list(settings.TEMPLATE_CONTEXT_PROCESSORS) +
                 list(settings.TEMPLATE_LOADERS) +
                 [settings.ROOT_URLCONF])


def find_url_callbacks(urls_module):
    urlpatterns = urls_module.urlpatterns
    hid_list = [urls_module.__name__]
    for pattern in urlpatterns:
        if isinstance(pattern, RegexURLPattern):
            hid_list.append(pattern.callback.__module__)
        elif isinstance(pattern, RegexURLResolver):
            hid_list += find_url_callbacks(pattern.urlconf_module)
    return hid_list

from django.core.urlresolvers import RegexURLPattern, RegexURLResolver

base_module_name = ".".join(compat.getenv("DJANGO_SETTINGS_MODULE", "settings").split(".")[:-1])
if base_module_name:
    base_module = __import__(base_module_name, {}, {}, ["urls"])
    urls = base_module.urls
else:
    import urls
hiddenimports += find_url_callbacks(urls)


logger.debug('%r', sorted(set(hiddenimports)))
