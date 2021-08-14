#-----------------------------------------------------------------------------
# Copyright (c) 2005-2021, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------
from pathlib import Path
import sys
import subprocess
import atexit
from PyInstaller.utils.tests import skip


@skip(reason='')
def test_hook_order(pyi_builder):
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', str(Path.with_name(__file__, 'hook_order_hooks'))])

    args = [sys.executable, '-m', 'pip', 'uninstall', 'pyi_example_package', '--yes', '-q', '-q', '-q']
    atexit.register(lambda: subprocess.run(args))

    pyi_builder.test_source(
        '''
        try:
            import pyi_example_package
        except:
            pass
        ''',
        pyi_args=['--additional-hooks-dir={}'.format(Path(__file__).with_name('hook_order_hooks'))],
    )
