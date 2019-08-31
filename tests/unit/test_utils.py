#-----------------------------------------------------------------------------
# Copyright (c) 2005-2019, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

from PyInstaller.utils import misc


def test_misc_build_from_template_file(tmpdir):
    tmpl = u"""
import os

env = os.getenv('{{ env_name }}', '{{ default }}')

print('{{not_changed}}')
"""
    expected = u"""
import os

env = os.getenv('FOO', 1)

print('{{not_changed}}')
"""

    tmpl_file = tmpdir.join('template_01.py').ensure()
    tmpl_file.write(tmpl)

    built_file = tmpdir.mkdir('build').join('template_01.py')

    misc.build_from_template_file(
        tmpl_file.realpath(),
        dict(
            env_name='FOO',
            default=1,
        ),
        built_file.realpath())
    assert expected == built_file.read_text('utf8')
