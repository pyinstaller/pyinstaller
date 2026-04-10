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

    def _divert_multiprocessing_helper():
        # We want to catch the two processes that are spawned by the multiprocessing code:
        # - the semaphore tracker, which cleans up named semaphores in the `spawn` multiprocessing mode
        # - the fork server, which keeps track of worker processes in the `forkserver` mode.
        # Both of these processes are started by spawning a new copy of the running executable, passing it the flags
        # from `_args_from_interpreter_flags` and then "-c" and an import statement.
        # Look for those flags and the import statement, then `exec()` the code ourselves.

        # First, look for the -c argument; this should come after executable path and arguments obtained from
        # `_args_from_interpreter_flags()` (which should be treated as variable due to their dependence on interpreter
        # flags, some of which may change with different PyInstaller build settings).
        try:
            command_switch_idx = sys.argv.index("-c")
        except ValueError:
            return

        # Check that -c switch is preceded by `_args_from_interpreter_flags()`.
        if set(sys.argv[1:command_switch_idx]) != set(_args_from_interpreter_flags()):
            return

        # "-c" switch should be followed by at least one more argument - the command to execute. Additional arguments
        # may follow, but they are of no concern here (i.e., the executed command will read them from `sys.argv` as
        # necessary).
        if len(sys.argv) <= command_switch_idx + 1:
            return
        command = sys.argv[command_switch_idx + 1]

        COMMAND_PREFIXES = (
            # semaphore/resource tracker
            'from multiprocessing.resource_tracker import main',
            # forkserver
            'from multiprocessing.forkserver import main',
            # forkserver in python >= 3.15.0a8 (backported to 3.13.13 and 3.14.4)
            # See: https://github.com/python/cpython/pull/148194
            'import sys; from multiprocessing.forkserver import main',
        )
        if not command.startswith(COMMAND_PREFIXES):
            return

        # Execute the given command and exit
        exec(command)
        sys.exit()

    def _freeze_support():
        # Check the arguments for known `multiprocessing` helper sub-processes; on match, execute its code and exit the
        # process by calling sys.exit()
        _divert_multiprocessing_helper()

        # Check the arguments for attempt at spawning a worker sub-process, and divert program flow on match.
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
