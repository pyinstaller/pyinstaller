"""
This module is used to reliably locate root directory of django projects by
using BASE_DIR or PROJECT_ROOT variables in settings.
"""

import django
django.setup()

# This allows to access all django settings even from the settings.py module.
from django.conf import settings

base_dir = getattr(settings, 'BASE_DIR', None)
if base_dir is None:
    base_dir = getattr(settings, 'PROJECT_ROOT', None)

print(repr(base_dir or ''))
