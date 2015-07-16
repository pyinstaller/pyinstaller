#-----------------------------------------------------------------------------
# Copyright (c) 2005-2015, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------


import os
import pytest

from PyInstaller.utils.tests import importorskip


# Directory with data for some tests.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


@pytest.mark.xfail(reason='still work in progress')
@importorskip('django')
def test_django(pyi_builder):
    # Django uses manage.py as the main script.
    script = os.path.join(_DATA_DIR, 'django_site', 'manage.py')
    # Create the exe, run django dev server and keep it running 2 sec.
    pyi_builder.test_script(script, app_name='django_site', pyi_args=['--name=django_site'],
                            app_args=['runserver'], runtime=2000)
