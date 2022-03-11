#-----------------------------------------------------------------------------
# Copyright (c) 2021-2022, PyInstaller Development Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: Apache-2.0
#-----------------------------------------------------------------------------

import subprocess
import sys
import io


class Popen(subprocess.Popen):

    # In windowed mode, force any unused pipes (stdin, stdout and stderr) to be DEVNULL instead of inheriting the
    # invalid corresponding handles from this parent process.
    if sys.platform == "win32" and not isinstance(sys.stdout, io.IOBase):

        def _get_handles(self, stdin, stdout, stderr):
            stdin, stdout, stderr = (subprocess.DEVNULL if pipe is None else pipe for pipe in (stdin, stdout, stderr))
            return super()._get_handles(stdin, stdout, stderr)


subprocess.Popen = Popen
