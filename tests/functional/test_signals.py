# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Copyright (c) 2005-2018, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

# Library imports
# ---------------
import signal

# Third-party imports
# -------------------
import pytest
from PyInstaller.utils.tests import skipif_win

signals = sorted([
    key for key in dir(signal)
    if key.startswith('SIG') and not key.startswith('SIG_')
])


@skipif_win
@pytest.mark.parametrize('signame', signals)
@pytest.mark.parametrize('ignore', [True, False])
def test_signal_handled(pyi_builder, signame, ignore):
    # xfail tests for signals that the bootloader does NOT forward
    if signame in ['SIGKILL', 'SIGSTOP']:
        pytest.xfail('{} cannot be caught'.format(signame))
    elif signame in ['SIGCHLD', 'SIGCLD']:
        pytest.xfail(
            'Messing with {} interferes with bootloader'.format(signame)
        )

    verb = 'ignored' if ignore else 'handled'
    app_name = 'test_signal_{}_{}'.format(verb, signame)
    pyi_args = ['--bootloader-ignore-signals'] if ignore else []

    pyi_builder.test_source(
        """
        from __future__ import print_function
        import psutil
        import signal
        import sys
        import time
        from signal import {signame}

        def eprint(*args): print(*args, file=sys.stderr)

        p = psutil.Process()
        eprint('[test_signal_handled_{signame}] process tree:')
        while p:
            eprint('-', p.name(), '(%s)' % p.pid)
            if p == p.parent():
                break
            p = p.parent()

        signalled = False

        def handle(signum, *args):
            eprint('handled signal', signum)
            global signalled
            signalled = True

        signal.signal({signame}, handle)

        ignore = {ignore}

        child = psutil.Process()
        parent = child.parent()

        if parent.name() == '{app_name}':
            # We are the forked child of the bootloader process.
            # Signal our parent process to mimic the behavior
            # of an external program signalling the process running
            # the executable that pyinstaller produced.
            target = parent
        elif ignore:
            # can't pytest.skip() from inside this process
            print('Bootloader did not fork; test is invalid')
            sys.exit(0)
        else:
            target = child

        eprint('signalling', target.name(), '(%s)' % target.pid)
        target.send_signal({signame})

        # sleep a bit to avoid exiting before the signal is delivered
        time.sleep(1)

        eprint('ignore:' ignore)
        eprint('signalled:', signalled)
        if ignore and signalled:
            raise Exception('signal {signame} not ignored')
        elif not ignore and not signalled:
            raise Exception('signal handler not called for {signame}')

        msg = 'ignored' if ignore else 'handled'
        eprint('bootloader', msg, 'signal successfully.')
        """.format(signame=signame, app_name=app_name, ignore=ignore),
        app_name=app_name,
        runtime=5,
        pyi_args=pyi_args)
