#-----------------------------------------------------------------------------
# Copyright (c) 2017-2023, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------


def _pyi_rthook():
    import sys

    import multiprocessing
    import multiprocessing.spawn

    from subprocess import _args_from_interpreter_flags

    # Prevent `spawn` from trying to read `__main__` in from the main script
    multiprocessing.process.ORIGINAL_DIR = None

    def _freeze_support():
        # We want to catch the two processes that are spawned by the multiprocessing code:
        # - the semaphore tracker, which cleans up named semaphores in the `spawn` multiprocessing mode
        # - the fork server, which keeps track of worker processes in the `forkserver` mode.
        # Both of these processes are started by spawning a new copy of the running executable, passing it the flags
        # from `_args_from_interpreter_flags` and then "-c" and an import statement.
        # Look for those flags and the import statement, then `exec()` the code ourselves.

        if (
            len(sys.argv) >= 2 and sys.argv[-2] == '-c' and sys.argv[-1].startswith(
                ('from multiprocessing.resource_tracker import main', 'from multiprocessing.forkserver import main')
            ) and set(sys.argv[1:-2]) == set(_args_from_interpreter_flags())
        ):
            exec(sys.argv[-1])
            sys.exit()

        if multiprocessing.spawn.is_forking(sys.argv):
            kwds = {}
            for arg in sys.argv[2:]:
                name, value = arg.split('=')
                if value == 'None':
                    kwds[name] = None
                else:
                    kwds[name] = int(value)
            multiprocessing.spawn.spawn_main(**kwds)
            sys.exit()

    multiprocessing.freeze_support = multiprocessing.spawn.freeze_support = _freeze_support


_pyi_rthook()
del _pyi_rthook
