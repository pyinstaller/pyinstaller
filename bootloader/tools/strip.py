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

from waflib import Task, TaskGen


def configure(conf):
    conf.find_program('strip')
    conf.env.append_value('STRIPFLAGS', '')


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
