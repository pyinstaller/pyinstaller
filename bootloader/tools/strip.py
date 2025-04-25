#-----------------------------------------------------------------------------
# Copyright (c) 2014-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

# Strip the binary after it is created.
#
# Based on waf's playground example:
# https://gitlab.com/ita1024/waf/-/blob/d976678d5f6ee5cf913b7828a7d4f345db7bf6de/playground/strip/strip_hack.py
import os

from waflib import Task, TaskGen


def configure(conf):
    # Look for the `strip` executable; first in the same directory as the C compiler executable, then in PATH.
    cc_path = os.path.dirname(conf.env.CC[0])
    environ = getattr(conf, 'environ', os.environ)
    env_paths = environ.get('PATH', '').split(os.pathsep)

    # Candidate name(s) for `strip` executable.
    strip_candidate_names = ['strip']

    # If we are using gcc-based or clang-based cross-compiler toolchain, prefer its version of `strip`, which should
    # have the same name prefix as the compiler executable (for example `powerpc64le-linux-gnu-gcc` would have
    # accompanying `powerpc64le-linux-gnu-strip`). The system might also have a "native" `strip` utility, which might
    # not be able to handle the executables produced by cross-compiler.
    if conf.env.CC_NAME == 'gcc' or conf.env.CC_NAME == 'clang':
        # The actual name of gcc/clang executable.
        cc_name = os.path.splitext(os.path.basename(conf.env.CC[0]))[0]
        # Replace gcc/clang part in the name.
        strip_name = cc_name.replace(conf.env.CC_NAME, 'strip')
        # If we have a candidate name different than plain strip, prepend it to the list. Explicitly guard against
        # failed substitution as well (strip_name == cc_name), to prevent any chance of erroneously using C compiler
        # executable in lieu of strip utility.
        if strip_name != 'strip' and strip_name != cc_name:
            strip_candidate_names.insert(0, strip_name)

    conf.find_program(strip_candidate_names, var='STRIP', path_list=[cc_path, *env_paths])

    # Additional flags to be passed to the `strip` command.
    conf.env.append_value('STRIPFLAGS', '')

    # On AIX, `strip` utility needs to be explicitly told to process 32-bit object files (-X32), 64-bit object files
    # (-X64), or either/both (-X32_64). Unless set via `OBJECT_MODE` environment variable, the default is 32-bit mode,
    # which results in an error when we build 64-bit bootloader. Therefore, explicitly set -X32_64 to work with
    # either 32-bit or 64-bit build. This should also eliminate potential mismatches between `OBJECT_MODE` setting
    # (which is honored by IBM's `xlc` compiler but not by `/opt/freeware/bin/gcc`) and `--target-arch=` command-line
    # option passed to `waf` (which can be used to force 64-bit build with `gcc`).
    if conf.env.DEST_OS == 'aix':
        conf.env.append_value('STRIPFLAGS', '-X32_64')


class StripTask(Task.Task):
    run_str = '${STRIP} ${STRIPFLAGS} ${SRC}'
    color = 'YELLOW'  # Same color as linking step
    no_errcheck_out = True

    def keyword(self):
        return 'Stripping binary'

    def runnable_status(self):
        if self in self.run_after:
            self.run_after.remove(self)

        ret = super().runnable_status()
        if ret == Task.ASK_LATER:
            return ret

        if self.generator.link_task.hasrun == Task.SUCCESS:
            # Linking step was executed - binary was (re)created); run the strip task.
            return Task.RUN_ME

        return Task.SKIP_ME


@TaskGen.feature('strip')
@TaskGen.after('apply_link')
def apply_strip_to_build(self):
    link_task = getattr(self, 'link_task', None)
    if link_task is None:
        return

    exe_node = self.link_task.outputs[0]

    # NOTE: original implementation sets both input and output to exe_node, but with version of `waf` we are using, this
    # raises dependency-cycle error.
    self.create_task('StripTask', exe_node)
