#-----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import PyInstaller.compat as compat
from PyInstaller.hooks.hookutils import logger

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
    if isinstance(urls_module, list):
        urlpatterns = urls_module
        hid_list = []
    else:
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

# This print statement is then parsed and evaluated as Python code.
print hiddenimports


logger.debug('%r', sorted(set(hiddenimports)))
