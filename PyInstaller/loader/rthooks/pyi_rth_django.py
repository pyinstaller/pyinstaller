#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


# This Django rthook was tested with Django 1.8.3.


import django.utils.autoreload


_old_restart_with_reloader = django.utils.autoreload.restart_with_reloader


def _restart_with_reloader(*args):
    import sys
    a0 = sys.argv.pop(0)
    try:
        return _old_restart_with_reloader(*args)
    finally:
        sys.argv.insert(0, a0)

# Override restart_with_reloader() function otherwise the app might
# complain that some commands do not exist. e.g. runserver.
django.utils.autoreload.restart_with_reloader = _restart_with_reloader
