#-----------------------------------------------------------------------------
# Copyright (c) 2017-2020, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import sys

# 'spawn' multiprocessing needs some adjustments on osx
import os
import re
import multiprocessing
import multiprocessing.spawn as spawn
from subprocess import _args_from_interpreter_flags

# prevent spawn from trying to read __main__ in from the main script
multiprocessing.process.ORIGINAL_DIR = None

def _freeze_support():
    # we want to catch the two processes that are spawned by the
    # multiprocessing code:
    # - the semaphore tracker, which cleans up named semaphores in
    #   the spawn multiprocessing mode
    # - the fork server, which keeps track of worker processes in
    #   forkserver mode.
    # both of these processes are started by spawning a new copy of the
    # running executable, passing it the flags from
    # _args_from_interpreter_flags and then "-c" and an import statement.
    # look for those flags and the import statement, then exec() the
    # code ourselves.

    if (len(sys.argv) >= 2 and
        sys.argv[-2] == '-c' and
        sys.argv[-1].startswith(
            ('from multiprocessing.semaphore_tracker import main',  # Py<3.8
             'from multiprocessing.resource_tracker import main',  # Py>=3.8
             'from multiprocessing.forkserver import main')) and
        set(sys.argv[1:-2]) == set(_args_from_interpreter_flags())):
        exec(sys.argv[-1])
        sys.exit()

    if spawn.is_forking(sys.argv):
        kwds = {}
        for arg in sys.argv[2:]:
            name, value = arg.split('=')
            if value == 'None':
                kwds[name] = None
            else:
                kwds[name] = int(value)
        spawn.spawn_main(**kwds)
        sys.exit()

multiprocessing.freeze_support = spawn.freeze_support = _freeze_support

# Bootloader unsets _MEIPASS2 for child processes to allow running
# PyInstaller binaries inside pyinstaller binaries.
# This is ok for mac or unix with fork() system call.
# But on Windows we need to overcome missing fork() function.

if sys.platform.startswith('win'):
    import multiprocessing.popen_spawn_win32 as forking
else:
    import multiprocessing.popen_fork as forking
    import multiprocessing.popen_spawn_posix as spawning



# Mix-in to re-set _MEIPASS2 from sys._MEIPASS.
class FrozenSupportMixIn():
    def __init__(self, *args, **kw):
        if hasattr(sys, 'frozen'):
            # We have to set original _MEIPASS2 value from sys._MEIPASS
            # to get --onefile mode working.
            os.putenv('_MEIPASS2', sys._MEIPASS)  # @UndefinedVariable
        try:
            super().__init__(*args, **kw)
        finally:
            if hasattr(sys, 'frozen'):
                # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                # available. In those cases we cannot delete the variable
                # but only set it to the empty string. The bootloader
                # can handle this case.
                if hasattr(os, 'unsetenv'):
                    os.unsetenv('_MEIPASS2')
                else:
                    os.putenv('_MEIPASS2', '')


# Patch forking.Popen to re-set _MEIPASS2 from sys._MEIPASS.
class _Popen(FrozenSupportMixIn, forking.Popen):
    pass

forking.Popen = _Popen

if not sys.platform.startswith('win'):
    # Patch spawning.Popen to re-set _MEIPASS2 from sys._MEIPASS.
    class _Spawning_Popen(FrozenSupportMixIn, spawning.Popen):
        pass

    spawning.Popen = _Spawning_Popen
