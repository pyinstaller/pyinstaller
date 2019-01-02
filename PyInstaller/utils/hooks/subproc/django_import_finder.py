#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


"""
This module parses all Django dependencies from the module mysite.settings.py.

NOTE: With newer version of Django this is most likely the part of PyInstaller
      that will be broken.

Tested with Django 1.8.
"""


import os

# Calling django.setup() avoids the exception AppRegistryNotReady()
# and also reads the user settings from DJANGO_SETTINGS_MODULE.
# https://stackoverflow.com/questions/24793351/django-appregistrynotready
import django
django.setup()

# This allows to access all django settings even from the settings.py module.
from django.conf import settings

from PyInstaller.utils.hooks import collect_submodules


hiddenimports = list(settings.INSTALLED_APPS) + \
                 list(settings.TEMPLATE_CONTEXT_PROCESSORS) + \
                 list(settings.TEMPLATE_LOADERS) + \
                 [settings.ROOT_URLCONF]


def _remove_class(class_name):
    return '.'.join(class_name.split('.')[0:-1])


### Changes in Django 1.7.

# Remove class names and keep just modules.
if hasattr(settings, 'AUTHENTICATION_BACKENDS'):
    for cl in settings.AUTHENTICATION_BACKENDS:
        cl = _remove_class(cl)
        hiddenimports.append(cl)
if hasattr(settings, 'DEFAULT_FILE_STORAGE'):
    cl = _remove_class(settings.DEFAULT_FILE_STORAGE)
    hiddenimports.append(cl)
if hasattr(settings, 'FILE_UPLOAD_HANDLERS'):
    for cl in settings.FILE_UPLOAD_HANDLERS:
        cl = _remove_class(cl)
        hiddenimports.append(cl)
if hasattr(settings, 'MIDDLEWARE_CLASSES'):
    for cl in settings.MIDDLEWARE_CLASSES:
        cl = _remove_class(cl)
        hiddenimports.append(cl)
# Templates is a dict:
if hasattr(settings, 'TEMPLATES'):
    for templ in settings.TEMPLATES:
        backend = _remove_class(templ['BACKEND'])
        # Include context_processors.
        if hasattr(templ, 'OPTIONS'):
            if hasattr(templ['OPTIONS'], 'context_processors'):
                # Context processors are functions - strip last word.
                mods = templ['OPTIONS']['context_processors']
                mods = [_remove_class(x) for x in mods]
                hiddenimports += mods
# Include database backends - it is a dict.
for v in settings.DATABASES.values():
    hiddenimports.append(v['ENGINE'])


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


# Add templatetags and context processors for each installed app.
for app in settings.INSTALLED_APPS:
    app_templatetag_module = app + '.templatetags'
    app_ctx_proc_module = app + '.context_processors'
    hiddenimports.append(app_templatetag_module)
    hiddenimports += collect_submodules(app_templatetag_module)
    hiddenimports.append(app_ctx_proc_module)


from django.core.urlresolvers import RegexURLPattern, RegexURLResolver


# Construct base module name - without 'settings' suffix.
base_module_name = '.'.join(os.environ['DJANGO_SETTINGS_MODULE'].split('.')[0:-1])
base_module = __import__(base_module_name, {}, {}, ["urls"])
urls = base_module.urls

# Find url imports.
hiddenimports += find_url_callbacks(urls)

# Deduplicate imports.
hiddenimports = list(set(hiddenimports))

# This print statement is then parsed and evaluated as Python code.
print(hiddenimports)
